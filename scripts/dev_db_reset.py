"""Development helper to reset the SQLite database."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.engine.url import make_url

from api.vysalytica.db.migrations import rollback_migrations, run_migrations


def delete_sqlite_if_present(db_url: str) -> None:
    try:
        parsed = make_url(db_url)
    except Exception:
        return
    database = parsed.database or ""
    if database and database not in {":memory:", "/:memory:"}:
        path = Path(database)
        if path.exists():
            path.unlink()
            print(f"Removed existing database at {path}")


def main() -> None:
    db_url = os.getenv("DATABASE_URL", "sqlite:///api/data/vysalytica.db")
    if db_url.startswith("sqlite"):
        delete_sqlite_if_present(db_url)
    rollback_migrations()
    run_migrations()


if __name__ == "__main__":
    main()
