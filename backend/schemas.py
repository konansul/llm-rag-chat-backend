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

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    role: str
    message_content: str

class MessageOut(BaseModel):
    message_id: int
    chat_id: int
    role: str
    created_at: datetime
    message_content: str