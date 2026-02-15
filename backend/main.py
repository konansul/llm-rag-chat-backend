from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from backend.routers import auth, chats, chat_title, messages, documents

app = FastAPI(
    title = "LLM and RAG Chatbot API",
    description = "Production ready backend for LLM based chat bots with Retrieval-Augmented Generation",
    version = "0.1.1"
)

app.add_middleware(CORSMiddleware, )

app.include_router(auth.router, tags = ["Users"])
app.include_router(chats.router, tags = ["Chats"])
app.include_router(chat_title.router, tags = ["Chat titles"])
app.include_router(messages.router, tags = ["Messages"])
app.include_router(documents.router, tags = ["Documents"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
