import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main

from app.database import Base
from app.database import get_db


def _get_test_database_url() -> str | None:
    return os.getenv("DATABASE_URL")


@pytest.fixture(scope="session")
def test_engine():
    database_url = _get_test_database_url()
    if not database_url:
        pytest.skip(
            "DATABASE_URL is not set; integration tests require a real database. "
            "Set DATABASE_URL to a Postgres connection string.",
            allow_module_level=True,
        )

    engine = create_engine(database_url)

    import app.models.user  # noqa: F401
    import app.models.calculation  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    main.app.dependency_overrides[get_db] = _override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
