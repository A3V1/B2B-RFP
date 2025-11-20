from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# create engine from DATABASE_URL (supports SQLite or Postgres)
engine = create_engine(settings.DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    # create tables from models
    try:
        from app.db import models
        models.Base.metadata.create_all(bind=engine)
    except Exception:
        # import errors should bubble to caller when appropriate
        raise

def get_engine():
    return engine
