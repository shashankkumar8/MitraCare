import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def make_database(url: str | None = None):
    url = url or os.getenv("DATABASE_URL", "sqlite:///./mitracare.db")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
