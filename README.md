# LLM and RAG Chatbot Backend

This project is a production-ready backend for an LLM-powered chat application with built-in Retrieval-Augmented Generation (RAG). It lets users hold multi-turn conversations with a large language model and, when needed, ground the model's answers in their own uploaded documents. Users register and log in, create separate chats, upload documents into a chat, and ask questions that are answered either from the model's general knowledge or from the retrieved content of their files. Each chat keeps its full message history and receives an automatically generated, periodically refreshed title. Documents are parsed, split into overlapping chunks, embedded, and stored as vectors, so that every question retrieves only the most relevant passages before the model composes a grounded reply.

The backend is built with FastAPI and PostgreSQL, using the `pgvector` extension for semantic vector search over document chunks. Language generation and text embeddings are powered by Google Gemini through the `google-genai` SDK, and document chunking is handled with LangChain's recursive text splitter. Authentication is stateless via JWT access tokens, and uploaded files are stored on disk with a database record and content hash for deduplication. A separate Streamlit application provides a ChatGPT-style user interface that talks to the backend exclusively through its REST API, so the API and the UI are fully decoupled and can be run or deployed independently.

---

## Requirements

- Docker, Docker Compose
- Python 3.10+

Core backend dependencies include:

```
fastapi
uvicorn
sqlalchemy
psycopg2-binary
pgvector
google-genai
langchain-text-splitters
pypdf
python-jose
passlib[bcrypt]
pydantic
python-dotenv
requests
streamlit
```

The FastAPI service exposes the REST API; the Streamlit app is an optional client UI built on top of the same API.

---

## Setup

### 1. Clone or download the repository

### 2. Start PostgreSQL (pgvector) through Docker

The database runs on the `pgvector/pgvector:pg16` image and is exposed on host port `5434`.

```bash
docker compose up -d
```

Enable the vector extension once (required for embedding storage and similarity search):

```bash
docker exec -it llm-chatbot psql -U llm-chatbot -d llm-chatbot -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Create and configure environment variables

This project uses environment variables for the database connection, authentication, LLM access, and upload limits. Create a `.env` file in the project root directory (the same level as `README.md`):

```bash
touch .env
```

Add the following variables. `GEMINI_API_KEY` is required for all AI features (chat replies, chat titles, embeddings, and RAG answers).

```env
DATABASE_URL=postgresql+psycopg2://llm-chatbot:llm-chatbot@localhost:5434/llm-chatbot

GEMINI_API_KEY=your_gemini_api_key_here
MODEL_NAME=gemini-2.5-flash

SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=180

ALLOWED_MIME=application/pdf,text/plain
BASE_STORAGE_DIR=storage
MAX_BYTES=10485760
MAX_BATCH=20
TITLE_REFRESH_EVERY_N_MESSAGES=6
```

### 4. Create a virtual environment and install requirements

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Initialize the database tables

Database tables are created automatically from the SQLAlchemy models on the first application startup via `Base.metadata.create_all`. Make sure the `vector` extension from step 2 is enabled before starting the server for the first time.

### 6. Start the backend API server

The backend will be available at `http://127.0.0.1:8000`. Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

```bash
uvicorn backend.main:app --reload --port 8000
```

### 7. Start the Streamlit chat UI (optional)

In a separate terminal, launch the ChatGPT-style client. It points to the backend at `http://127.0.0.1:8000` by default.

```bash
streamlit run backend/app.py
```

---

## Database Schema

The backend uses a PostgreSQL database with the `pgvector` extension to persist users, chats, messages, documents, and their embedded chunks. Every chat, message, and document is scoped to the owning user, so each account only ever sees its own conversations and files.

Users are stored in the `users` table with a unique username and email and a bcrypt-hashed password. Each user can own many `chats`, and each chat stores a title, a creation timestamp, and title-management metadata (`last_titled_message_id` and `is_title_locked`) that control when the LLM regenerates the conversation title. Messages belong to a chat through the `messages` table, which records the `role` (`user` or `assistant`), the message content, and a timestamp, giving each conversation a complete, ordered history.

Uploaded files are stored as `documents`, which keep the original title and source name, the MIME type, an on-disk `storage_path` for the binary and a `processed_text_path` for the extracted plain text, the file size, and a unique `sha256` hash used for deduplication. A `status` enum (`uploaded → processing → ready → failed`) tracks each document through the ingestion pipeline. Documents are attached to specific chats through the `chat_documents` link table, which carries an `enabled` flag so a document can be toggled on or off as a retrieval source for a given chat.

The core of the RAG layer is the `document_chunks` table. When a document is processed, its text is split into overlapping chunks, each chunk is embedded with Gemini, and the resulting vector is stored in a `pgvector` column alongside the chunk's index and raw content. At query time, the user's question is embedded and compared against these vectors by cosine distance to retrieve the top matching chunks, which are then supplied to the model as grounding context.

---

## Project Structure

```
llm-rag-chat-backend/
│
├── backend/                              # FastAPI backend + Streamlit client
│   ├── main.py                           # FastAPI entrypoint, CORS configuration, router registration
│   ├── app.py                            # Streamlit chat UI (ChatGPT-style client for the API)
│   ├── data_access.py                    # APIClient — typed HTTP client used by the Streamlit UI
│   │
│   ├── routers/                          # HTTP layer — routers and request/response handling
│   │   ├── auth.py                       # Register, login, logout, /me (JWT authentication)
│   │   ├── chats.py                      # Chat create/list/get/delete and streamed answer generation
│   │   ├── chat_title.py                 # LLM-generated and periodically refreshed chat titles
│   │   ├── messages.py                   # Message history read and append endpoints
│   │   ├── documents.py                  # Document upload, processing (chunk + embed), and RAG Q&A
│   │   └── helpers.py                    # Shared router utilities and the auth dependency
│   │
│   ├── services/
│   │   ├── llm_client/
│   │   │   └── gemini_client.py          # Google Gemini client — chat reply, chat title, RAG answer
│   │   └── rag/
│   │       ├── document_processor.py     # Text extraction, recursive chunking, and Gemini embeddings
│   │       └── should_use_rag.py         # Decides whether a question requires document retrieval
│   │
│   └── database/
│       ├── db.py                         # SQLAlchemy engine/session factory and create_all bootstrap
│       ├── models.py                     # ORM models: User, Chats, Messages, Documents, ChatDocument, DocumentChunks (pgvector)
│       ├── schemas.py                    # Pydantic request/response models
│       └── security.py                   # Password hashing (bcrypt) and JWT creation/verification
│
├── db/
│   └── init/                             # Postgres init scripts mount (docker-entrypoint-initdb.d)
│
├── storage/                              # Uploaded files and extracted text stored on disk
├── test_files/                           # Sample documents for exercising the RAG pipeline
├── docker-compose.yml                    # pgvector/pgvector:pg16 database container definition
└── README.md
```

---

## API Endpoints

### 1. Authentication

```
POST   /auth/register     Register a new user (username, email, password)
POST   /auth/login        Login with email and password, receive a JWT access token
GET    /auth/me           Get the current authenticated user
POST   /auth/logout       Logout (client-side token removal)
```

### 2. Chats

```
POST   /chats                          Create a new chat
GET    /chats                          List the current user's chats
GET    /chats/{chat_id}                Get a single chat
DELETE /chats/{chat_id}                Delete a chat and all of its messages
POST   /chats/{chat_id}/generate       Generate an assistant reply (RAG-aware, streamed)
POST   /chats/{chat_id}/title/refresh  Regenerate the chat title with the LLM
```

### 3. Messages

```
GET    /chats/{chat_id}/messages       List all messages in a chat
POST   /chats/{chat_id}/messages       Append a message to a chat
```

### 4. Documents & RAG

```
POST   /chats/{chat_id}/documents/upload   Upload a document into a chat
POST   /documents/{document_id}/process    Extract text, chunk it, embed the chunks, and store vectors
POST   /documents/{document_id}/ask        Ask a question answered from the document via retrieval
```

---

## Notes

Answer generation is RAG-aware. Before responding, the backend runs a lightweight `should_use_rag` check to decide whether a question can be answered from the model's own knowledge or requires retrieval from the user's documents. When retrieval is triggered, the question is embedded, compared against the document chunks by cosine similarity in `pgvector`, and the top-matching passages are passed to Gemini as grounding context so the reply stays anchored to the source material.

Document processing uses LangChain's `RecursiveCharacterTextSplitter` with a chunk size of 1500 characters and 150 characters of overlap, which preserves context across chunk boundaries. Both document chunks and user queries are embedded with the `gemini-embedding-001` model, using distinct task types (`RETRIEVAL_DOCUMENT` for chunks and `RETRIEVAL_QUERY` for questions) to improve retrieval quality.

Chat titles are generated by the LLM and refreshed automatically after a configurable number of messages (`TITLE_REFRESH_EVERY_N_MESSAGES`), unless a title has been manually locked. Uploaded files are validated against a configurable `ALLOWED_MIME` list and a maximum size, stored on disk under `BASE_STORAGE_DIR`, and deduplicated with a `sha256` hash so the same file is never ingested twice.

The FastAPI backend and the Streamlit UI are fully decoupled and communicate exclusively over the REST API using a Bearer token. The Streamlit client stores the token in its session state and can be pointed at any running instance of the backend, so the two can be developed, run, and deployed independently.
