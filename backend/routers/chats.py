from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

from backend.database.db import get_db
from backend.database.models import Chats, Messages, User
from backend.schemas import ChatCreate, ChatOut
from backend.services.gemini_client import generate_reply
from backend.database.security import get_current_user

router = APIRouter()

def _get_user_chat_or_404(db: Session, chat_id: int, user_id: int) -> Chats:
    chat = (
        db.query(Chats)
        .filter(and_(Chats.chat_id == chat_id, Chats.user_id == user_id))
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.post("/chats", response_model=ChatOut)
def create_chat(
    chat: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_title: Optional[str] = getattr(chat, "chat_title", None)
    if chat_title is None:
        chat_title = getattr(chat, "title", None)

    chat_db = Chats(
        user_id=current_user.user_id,
        chat_title=(chat_title or "New chat"),
    )

    db.add(chat_db)
    db.commit()
    db.refresh(chat_db)
    return chat_db


@router.get("/chats", response_model=List[ChatOut])
def get_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chats = (
        db.query(Chats)
        .filter(Chats.user_id == current_user.user_id)
        .order_by(Chats.created_at.desc())
        .all()
    )
    return chats

@router.get("/chats/{chat_id}", response_model=ChatOut)
def get_chat_id(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_user_chat_or_404(db, chat_id, current_user.user_id)


@router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _get_user_chat_or_404(db, chat_id, current_user.user_id)

    db.query(Messages).filter(Messages.chat_id == chat_id).delete(synchronize_session=False)

    db.delete(chat)
    db.commit()
    return None

@router.post("/chats/{chat_id}/generate")
def generate(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = _get_user_chat_or_404(db, chat_id, current_user.user_id)

    N = 20
    rows = (
        db.query(Messages)
        .filter(Messages.chat_id == chat_id)
        .order_by(Messages.created_at.desc())
        .limit(N)
        .all()
    )

    rows = list(reversed(rows))

    history = [{"role": m.role, "content": m.message_content} for m in rows]

    reply = generate_reply(history)

    assistant_msg = Messages(
        chat_id=chat_id,
        role="assistant",
        message_content=reply,
    )

    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return {"reply": reply, "message_id": assistant_msg.message_id}