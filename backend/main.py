from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from backend.routers import auth, chats, messages

app = FastAPI(
    title = "LLM and RAG Chat Platform API",
    description = "Production ready backend for LLM based chat bots with Retrieval-Augmented Generation",
    version = "0.1.0"
)

app.add_middleware(
    CORSMiddleware,
)
app.include_router(auth.router, tags = ["Users"])
app.include_router(chats.router, tags = ["Chats"])
app.include_router(messages.router, tags = ["Messages"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
