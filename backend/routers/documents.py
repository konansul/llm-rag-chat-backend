import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, HTTPException
from pathlib import Path

from backend.database.models import User, Documents, ChatDocument, DocumentChunks
from .helpers import _get_user_chat_or_404, _sha256_bytes, retrieve_top_k, build_context
from backend.database.security import get_current_user
from backend.database.schemas import UploadDocumentResponse, ProcessDocumentResponse, AskRequest, AskResponse
from fastapi.params import Depends, File, Body
from sqlalchemy.orm import Session

from backend.database.db import get_db

from backend.services.rag.document_processor import extract_text_from_file, chunk_splitter, embed_text, embed_query
from backend.services.llm_client.gemini_client import answer_question

router = APIRouter()

BASE_STORAGE_DIR = Path(os.getenv("BASE_STORAGE_DIR"))
ALLOWED_MIME = os.getenv("ALLOWED_MIME")
MAX_BYTES = int(os.getenv("MAX_BYTES"))

@router.post("/chats/{chat_id}/documents/upload", response_model = UploadDocumentResponse)
def upload_document_to_chat (
        chat_id: int,
        file: UploadFile = File(...),
        title: str = "",
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    _ = _get_user_chat_or_404(db, chat_id, current_user.user_id)

    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIME:
        raise HTTPException( status_code = 415, detail = f"Unsupported file type: {mime}. Allowed types: {ALLOWED_MIME}", )

    data = file.file.read()
    if not data:
        raise HTTPException( status_code = 400, detail = f"Empty file.")

    if len(data) > MAX_BYTES:
        raise HTTPException(status_code = 413, detail = f"File too large. Expected {MAX_BYTES} bytes, received {len(data)} bytes")

    sha = _sha256_bytes(data)
    original_name = file.filename or "uploaded_file"

    existing = db.query(Documents).filter(Documents.sha256 == sha).first()

    if existing:
        doc = existing

    else:
        BASE_STORAGE_DIR.mkdir(parents = True, exist_ok = True)
        safe_name = "".join(c for c in original_name if c.isalnum() or c in ("-", "_", ".", " ")).strip()
        if not safe_name:
            safe_name = "file"

        storage_name = f"{current_user.user_id}_{sha}_{safe_name}"
        storage_path = BASE_STORAGE_DIR / storage_name
        storage_path.write_bytes(data)

        doc = Documents(
            user_id = current_user.user_id,
            title=(title.strip() if title else Path(original_name).stem) or "Untitled",
            source_name = original_name,
            mime_type = mime,
            storage_path = str(storage_path),
            processed_text_path = None,
            file_size = len(data),
            sha256 = sha,
            status = "uploaded",
            created_at = datetime.utcnow(),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

    link = (
        db.query(ChatDocument)
        .filter(ChatDocument.chat_id == chat_id, ChatDocument.document_id == doc.document_id)
        .first()
    )
    if link is None:
        link = ChatDocument(chat_id=chat_id, document_id=doc.document_id, enabled=True)
        db.add(link)
        db.commit()

    return {
        "document": doc,
        "chat_id": chat_id,
    }


@router.post("/documents/{document_id}/process", response_model = ProcessDocumentResponse)
def process_document (
        document_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    doc = db.query(Documents).filter(Documents.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code = 404, detail = f"Document {document_id} not found")

    path = doc.storage_path

    if not path:
        raise HTTPException(status_code = 400, detail = "Document has no file path")

    text = extract_text_from_file(path, "")

    chunks = chunk_splitter(text)

    embeddings = embed_text(chunks = chunks)

    if len(chunks) != len(embeddings):
        raise HTTPException(status_code = 500, detail = "Chunks/embeddings count mismatch")

    rows = []
    now = datetime.utcnow()
    for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
        rows.append(
            DocumentChunks(
                document_id=document_id,
                chunk_index=i,
                content=chunk_text,
                embedding=emb,
                created_at=now,
            )
        )

    db.add_all(rows)
    db.commit()

    return {
        "document_id": document_id,
        "chunks_saved": len(rows),
        "vector_dim": len(embeddings[0]) if embeddings else 0,
        "status": "ready",
    }


@router.post("/documents/{document_id}/ask", response_model=AskResponse)
def ask_document(
    document_id: int,
    payload: AskRequest = Body(...),
    db: Session = Depends(get_db),
):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is empty")

    qvec = embed_query(question)

    top_chunks = retrieve_top_k(db, document_id=document_id, query_vec=qvec, k=payload.k)

    if not top_chunks:
        return {
            "document_id": document_id,
            "question": question,
            "answer": "I don't know based on the document.",
            "sources": [],
        }

    context = build_context(top_chunks)

    answer = answer_question( question, context)

    return {
        "document_id": document_id,
        "question": question,
        "answer": answer,
        "sources": [
            {
                "chunk_id": c.chunk_id,
                "chunk_index": c.chunk_index,
            }
            for c in top_chunks
        ],
    }



