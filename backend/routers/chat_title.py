from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from backend.database.db import get_db
from backend.database.models import Chats, Messages, User
from backend.database.security import get_current_user
from backend.routers.helpers import _get_user_chat_or_404, refresh_chat_title_core

from backend.database.schemas import ChatTitleUpdate, ChatTitleRefreshOut, ChatOut

router = APIRouter()

@router.patch("/chats/{chat_id}/title", response_model=ChatOut)
def update_chat_title_manual(
    chat_id: int,
    payload: ChatTitleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _get_user_chat_or_404(db, chat_id, current_user.user_id)

    chat.chat_title = payload.chat_title.strip()
    chat.is_title_locked = True

    last_msg = (
        db.query(Messages)
        .filter(Messages.chat_id == chat_id)
        .order_by(Messages.message_id.desc())
        .first()
    )
    chat.last_titled_message_id = last_msg.message_id if last_msg else None

    db.commit()
    db.refresh(chat)
    return chat


@router.post("/chats/{chat_id}/title/refresh", response_model=ChatTitleRefreshOut)
def refresh_chat_title_auto(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = _get_user_chat_or_404(db, chat_id, current_user.user_id)

    result = refresh_chat_title_core(db, chat, chat_id)
    return result