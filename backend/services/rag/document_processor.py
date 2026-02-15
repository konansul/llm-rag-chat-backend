from __future__ import annotations

import os
from pathlib import Path
from typing import List

from google import genai
from google.genai import types

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


from dotenv import load_dotenv
load_dotenv()

MAX_BATCH = int(os.getenv("MAX_BATCH"))

client = genai.Client(api_key = os.getenv("GEMINI_API_KEY"))


def extract_text_from_file(path: str, mime_type: str) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File {path} does not exist")

    if mime_type == "text/plain" or path.suffix.lower() == ".txt":
        return path.read_text()

    if mime_type == "application/pdf" or path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        parts = [ ]
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()

    raise ValueError(f"Unsupported file type: {mime_type}")


def chunk_splitter(text: str, chunk_size: int = 1500, chunk_overlap: int = 150) -> List[str]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap,
    )

    chunks = splitter.split_text(text)

    return chunks


def embed_text(
        chunks: List[str],
        model: str = "gemini-embedding-001",
        task_type: str = "RETRIEVAL_DOCUMENT",
        batch_size: int = MAX_BATCH,
)-> List[List[float]]:

    embeddings: List[List[float]] = []

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]

        result = client.models.embed_content(
            model = model,
            contents = batch,
            config = types.EmbedContentConfig(task_type = task_type)
        )

        for vector in result.embeddings:
            embeddings.append(vector.values)

    return embeddings


def embed_query(text: str, model: str = "gemini-embedding-001", task_type: str = "RETRIEVAL_QUERY"):

    result = client.models.embed_content(
        model=model,
        contents=[text],
        config=types.EmbedContentConfig(task_type=task_type)
    )

    return result.embeddings[0].values

