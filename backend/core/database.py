import sqlite3
from pathlib import Path
from contextlib import contextmanager
from .config import settings


def get_db_path():
    """Extract SQLite path from database URL."""
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return "database/leads.db"


@contextmanager
def get_db_connection():
    """Context manager for SQLite connections."""
    db_path = get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
