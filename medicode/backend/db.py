"""SQLite engine + session helpers."""

from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

DB_PATH = Path(__file__).resolve().parent.parent / "medicode.db"
ENGINE = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create all tables. Import models first so they register on metadata."""
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(ENGINE)


def get_session() -> Session:
    # expire_on_commit=False keeps loaded attributes readable after commit, so
    # we can serialize a node (to_node) following a commit without a re-fetch.
    return Session(ENGINE, expire_on_commit=False)
