import os
from google import genai
from fastapi import Depends, APIRouter, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

from backend.database.db import get_db, SessionLocal
from backend.database.models import Chats, Messages, User, Documents, ChatDocument
from backend.routers.helpers import _get_user_chat_or_404, _background_refresh_title, retrieve_top_k, build_context
from backend.database.schemas import ChatCreate, ChatOut
from backend.services.llm_client.gemini_client import generate_reply, answer_question
from backend.database.security import get_current_user
from backend.services.rag.document_processor import embed_query
from backend.services.rag.should_use_rag import should_use_rag

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
router = APIRouter()
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = (
        db.query(Chats)
        .filter(and_(Chats.chat_id == chat_id, Chats.user_id == current_user.user_id))
        .first()
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    last_user_msg = (
        db.query(Messages)
        .filter(Messages.chat_id == chat_id, Messages.role == "user")
        .order_by(Messages.message_id.desc())
        .first()
    )
    if last_user_msg is None:
        raise HTTPException(status_code=400, detail="No user message to answer")

    question = (last_user_msg.message_content or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is empty")

    chat_docs = (
        db.query(ChatDocument)
        .filter(ChatDocument.chat_id == chat_id, ChatDocument.enabled == True)
        .all()
    )

    doc_ids = [cd.document_id for cd in chat_docs]

    docs = []
    if doc_ids:
        docs = db.query(Documents).filter(Documents.document_id.in_(doc_ids)).all()

    doc_brief = [{"document_id": d.document_id, "title": d.title} for d in docs]

    use_rag = bool(docs) and should_use_rag(client, question, doc_brief)

    used_doc_id = None
    sources = []

    if use_rag:
        document_id = docs[0].document_id
        used_doc_id = document_id

        qvec = embed_query(text = question)
        top_chunks = retrieve_top_k(db, document_id=document_id, query_vec=qvec)
        if top_chunks:
            context = build_context(top_chunks)
            reply = answer_question(question=question, context=context)
            sources = [{"chunk_id": c.chunk_id, "chunk_index": c.chunk_index} for c in top_chunks]
        else:
            reply = "I don't know based on the document."
            sources = []
    else:
        N = 50
        rows = (
            db.query(Messages)
            .filter(Messages.chat_id == chat_id)
            .order_by(Messages.message_id.desc())
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

    background_tasks.add_task(_background_refresh_title, chat_id, current_user.user_id)

    return {
        "reply": reply,
        "message_id": assistant_msg.message_id,
        "used_rag": use_rag,
        "document_id": used_doc_id,
        "sources": sources,
    }