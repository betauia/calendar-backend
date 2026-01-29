# infrastructure/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./events.db"

engine = create_engine(
    DATABASE_URL,
    future=True,   # SQLAlchemy 2.0 behavior
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
