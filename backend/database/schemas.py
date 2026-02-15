from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str = Field(min_length = 3, max_length = 128)
    email: EmailStr
    password: str = Field(min_length = 8, max_length = 128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

class LoginResponseToken(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CurrentUser(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

class LogoutResponse(BaseModel):
    status: str = "ok"

class ChatCreate(BaseModel):
    chat_title: Optional[str] = None

class ChatOut(BaseModel):
    chat_title: str
    chat_id: int
    created_at: datetime
    is_title_locked: bool | None = None
    last_titled_message_id: int | None = None

    class Config:
        from_attributes = True

class ChatTitleUpdate(BaseModel):
    chat_title: str = Field(min_length=1, max_length=80)

class ChatTitleRefreshOut(BaseModel):
    chat_id: int
    chat_title: str
    updated: bool
    reason: str

class MessageCreate(BaseModel):
    role: str
    message_content: str

class MessageOut(BaseModel):
    message_id: int
    chat_id: int
    role: str
    created_at: datetime
    message_content: str

class DocumentOut(BaseModel):
    document_id: int
    user_id: int
    title: str
    source_name: str
    mime_type: str
    storage_path: str
    processed_text_path: Optional[str] = None
    file_size: int
    sha256: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatDocumentOut(BaseModel):
    chat_id: int
    document_id: int
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UploadDocumentResponse(BaseModel):
    document: DocumentOut
    chat_id: int

class ProcessDocumentResponse(BaseModel):
    document_id: int
    chunks_saved: int
    vector_dim: int

class AskRequest(BaseModel):
    question: str
    k: int = 5

class AskResponse(BaseModel):
    document_id: int
    question: str
    answer: str
    sources: list[dict]