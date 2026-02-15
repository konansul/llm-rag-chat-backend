import os
import hashlib

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, select

from backend.database.db import SessionLocal
from backend.database.models import Chats, Messages, DocumentChunks
from backend.services.llm_client.gemini_client import generate_chat_title

TITLE_REFRESH_EVERY_N_MESSAGES = int(os.getenv("TITLE_REFRESH_EVERY_N_MESSAGES"))

def _get_user_chat_or_404(db: Session, chat_id: int, user_id: int) -> Chats:
    chat = (
        db.query(Chats)
        .filter(and_(Chats.chat_id == chat_id, Chats.user_id == user_id))
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

def _count_messages(db: Session, chat_id: int) -> int:
    return db.query(Messages).filter(Messages.chat_id == chat_id).count()

def _get_recent_history_for_title(db: Session, chat_id: int, limit: int = 12) -> list[dict]:
    rows = (
        db.query(Messages)
        .filter(Messages.chat_id == chat_id)
        .order_by(Messages.created_at.asc())
        .limit(limit)
        .all()
    )
    return [{"role": m.role, "content": m.message_content} for m in rows]

def _background_refresh_title(chat_id: int, user_id: int):
    db = SessionLocal()
    try:
        chat = _get_user_chat_or_404(db, chat_id, user_id)
        refresh_chat_title_core(db, chat, chat_id)
    finally:
        db.close()


def retrieve_top_k(db, document_id: int, query_vec: list[float], k: int = 5):
    sql_statement = (
        select(DocumentChunks)
        .where(DocumentChunks.document_id == document_id)
        .order_by(DocumentChunks.embedding.cosine_distance(query_vec))
        .limit(k)
    )
    return db.execute(sql_statement).scalars().all()


def build_context(chunks) -> str:
    return "\n\n".join(
        f"[chunk {c.chunk_index}]\n{c.content}"
        for c in chunks
    )

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def refresh_chat_title_core(db: Session, chat: Chats, chat_id: int) -> dict:
    if getattr(chat, "is_title_locked", False):
        return {"updated": False, "reason": "title_locked_by_user", "chat_title": chat.chat_title}

    total = db.query(Messages).filter(Messages.chat_id == chat_id).count()
    if total < 2:
        return {"updated": False, "reason": "not_enough_messages", "chat_title": chat.chat_title}

    last_titled_id = getattr(chat, "last_titled_message_id", None)

    last_msg = (
        db.query(Messages)
        .filter(Messages.chat_id == chat_id)
        .order_by(Messages.message_id.desc())
        .first()
    )
    if not last_msg:
        return {"updated": False, "reason": "no_messages", "chat_title": chat.chat_title}

    if last_titled_id is not None:
        since = (
            db.query(Messages)
            .filter(Messages.chat_id == chat_id, Messages.message_id > last_titled_id)
            .count()
        )
        if since < TITLE_REFRESH_EVERY_N_MESSAGES:
            return {
                "updated": False,
                "reason": f"cooldown_not_reached({since}/{TITLE_REFRESH_EVERY_N_MESSAGES})",
                "chat_title": chat.chat_title,
            }

    history = _get_recent_history_for_title(db, chat_id, limit=12)
    new_title = (generate_chat_title(history) or "").strip()

    new_title = new_title.splitlines()[0].strip()
    words = new_title.replace("—", " ").replace("-", " ").split()
    new_title = " ".join(words[:3]).strip()

    if not new_title:
        return {"updated": False, "reason": "empty_title", "chat_title": chat.chat_title}

    chat.chat_title = new_title
    chat.last_titled_message_id = last_msg.message_id

    db.commit()
    db.refresh(chat)

    return {"updated": True, "reason": "auto_refreshed", "chat_title": chat.chat_title}