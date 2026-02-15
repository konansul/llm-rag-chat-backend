from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean, Enum, PrimaryKeyConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from  pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    username: Mapped[str] = mapped_column(String, unique = True)
    email: Mapped[str] = mapped_column(String, unique = True, nullable = False)
    password: Mapped[str] = mapped_column(String, nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow)


class Chats(Base):
    __tablename__ = "chats"
    chat_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id", ondelete = "CASCADE"))
    chat_title: Mapped[str] = mapped_column(String, nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow)
    last_titled_message_id: Mapped[int] = mapped_column(Integer, nullable  =True)
    is_title_locked: Mapped[Boolean] = mapped_column(Boolean, nullable = False, default = False)


class Messages(Base):
    __tablename__ = "messages"
    message_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.chat_id", ondelete = "CASCADE"))
    role: Mapped[str] = mapped_column(String)
    message_content: Mapped[str] = mapped_column(String, nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow)


class Documents(Base):
    __tablename__ = "documents"
    document_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), index = True)
    title: Mapped[str] = mapped_column(String)
    source_name: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String)
    processed_text_path: Mapped[str] = mapped_column(String, nullable = True)
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String, unique = True, index = True)
    status: Mapped[str] = mapped_column(Enum("uploaded", "processing", "ready", "failed", name = "doc_status"), default = "uploaded", nullable = False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow)


class ChatDocument(Base):
    __tablename__ = "chat_documents"
    __table_args__ = (PrimaryKeyConstraint("chat_id", "document_id"), )
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.chat_id"), index = True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.document_id"), index = True)
    enabled: Mapped[bool] = mapped_column(Boolean, default = True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow)


class  DocumentChunks(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (Index("ix_document_chunks_doc_idx", "document_id", "chunk_index"), )
    chunk_id: Mapped[int] = mapped_column(Integer, primary_key = True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.document_id"), index = True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(String)
    embedding: Mapped[list[float]] = mapped_column(Vector(3072))
    created_at: Mapped[datetime] = mapped_column(DateTime, default = datetime.utcnow)