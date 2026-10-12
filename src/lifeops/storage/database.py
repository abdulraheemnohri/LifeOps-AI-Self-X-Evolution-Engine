import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from lifeops.storage.models import Base

DEFAULT_DB_URL = os.environ.get("DATABASE_URL", "sqlite:///data/lifeops.db")

def get_engine(db_url: str = DEFAULT_DB_URL):
    if db_url.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)
        return create_engine(db_url, connect_args={"check_same_thread": False}, echo=False)
    return create_engine(db_url, echo=False)

def init_db(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return engine

def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
