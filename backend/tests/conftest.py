"""
Test configuration and shared fixtures.

Provides an isolated in-memory SQLite database and session for
each test function, ensuring tests are independent and repeatable.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base


@pytest.fixture(name="db")
def db_session():
    """
    Create a fresh in-memory database and session for each test.

    Tables are created before the test and dropped after, so each
    test starts with a completely clean slate.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
