"""
Database configuration and session management
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from api.vysalytica.config import DEFAULT_DATABASE_URL, get_database_url

# Database configuration
DATABASE_URL = get_database_url()
sqlite_path: Path | None = None

if DATABASE_URL == DEFAULT_DATABASE_URL:
    project_root = Path(__file__).resolve().parents[2]
    sqlite_path = (project_root / "api" / "data" / "vysalytica.db").resolve()
elif DATABASE_URL.startswith("sqlite"):
    try:
        parsed_url = make_url(DATABASE_URL)
    except Exception:
        parsed_url = None
    if parsed_url is not None:
        database = parsed_url.database
        if (
            database
            and database not in {":memory:", "/:memory:"}
            and not database.startswith("file:")
        ):
            candidate_path = Path(database)
            if not candidate_path.is_absolute():
                candidate_path = candidate_path.resolve()
            sqlite_path = candidate_path

if sqlite_path is not None:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = str(URL.create(drivername="sqlite", database=str(sqlite_path)))

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine with appropriate settings
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Declarative base for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database sessions.

    Usage:
        db = next(get_db())
        try:
            # use db
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
