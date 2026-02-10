from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    username: Mapped[str] = mapped_column(String, unique = True)
    email: Mapped[str] = mapped_column(String, unique = True, nullable = False)
    password: Mapped[str] = mapped_column(String, nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Chats(Base):
    __tablename__ = "chats"
    chat_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"))
    chat_title: Mapped[str] = mapped_column(String, nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Messages(Base):
    __tablename__ = "messages"
    message_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.chat_id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String)
    message_content: Mapped[str] = mapped_column(String, nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
