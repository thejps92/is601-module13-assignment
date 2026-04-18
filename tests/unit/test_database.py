from __future__ import annotations

from sqlalchemy import text

from app.config import settings
from app.database import get_db, get_engine, get_sessionmaker


def test_get_engine_and_sessionmaker_with_sqlite(tmp_path):
    get_engine.cache_clear()

    db_file = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_file}")
    assert engine.dialect.name == "sqlite"

    SessionLocal = get_sessionmaker(engine)
    session = SessionLocal()
    try:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        session.close()


def test_get_db_yields_and_closes_session(tmp_path):
    get_engine.cache_clear()

    db_file = tmp_path / "test2.db"
    previous_url = settings.DATABASE_URL
    try:
        settings.DATABASE_URL = f"sqlite:///{db_file}"

        gen = get_db()
        session = next(gen)
        assert session.execute(text("SELECT 1")).scalar_one() == 1
        gen.close()
    finally:
        settings.DATABASE_URL = previous_url
