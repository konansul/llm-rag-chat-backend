from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

database_url = "postgresql+psycopg://llm-chatbot:llm-chatbot@localhost:5434/llm-chatbot"

engine = create_engine(database_url, echo = True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend.database.models import Base
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()