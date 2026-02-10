from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from backend.database.models import Messages, Chats
from backend.schemas import MessageOut, MessageCreate
from backend.database.db import get_db

router = APIRouter()

@router.get("/chats/{chat_id}/messages", response_model=List[MessageOut])
def get_messages(chat_id: int, limit: int = 50, db: Session = Depends(get_db)):
    chat = db.query(Chats).filter(Chats.chat_id == chat_id).first()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = (
        db.query(Messages)
        .filter(Messages.chat_id == chat_id)
        .order_by(Messages.created_at.asc())
        .limit(limit)
        .all()
    )
    return messages


@router.post("/chats/{chat_id}/messages", response_model=MessageOut)
def create_messages(chat_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    chat = db.query(Chats).filter(Chats.chat_id == chat_id).first()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    message_db = Messages(
        chat_id=chat_id,
        role=message.role,
        message_content=message.message_content,
    )

    db.add(message_db)
    db.commit()
    db.refresh(message_db)

    return message_db