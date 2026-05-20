from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config

engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_context():
    """Context provider safe boundary for SQL sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
