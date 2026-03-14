"""Database models and session management."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from content_engine.config import AppConfig


class Base(DeclarativeBase):
    pass


class SourceStatus(PyEnum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    TRANSCRIBED = "transcribed"
    CLIPPED = "clipped"
    FAILED = "failed"


class ClipStatus(PyEnum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    RENDERED = "rendered"
    UPLOADED = "uploaded"
    FAILED = "failed"


class Source(Base):
    """A source video/audio that clips are extracted from."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    channel: Mapped[str | None] = mapped_column(String(300))
    duration: Mapped[float | None] = mapped_column(Float)
    file_path: Mapped[str | None] = mapped_column(String(1024))
    transcript_path: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus), default=SourceStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Clip(Base):
    """An extracted clip from a source."""

    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024))
    title: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    virality_score: Mapped[float | None] = mapped_column(Float)
    transcript_segment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ClipStatus] = mapped_column(
        Enum(ClipStatus), default=ClipStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class PlatformAccount(Base):
    """OAuth credentials for a platform account (supports multi-account scaling)."""

    __tablename__ = "platform_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # youtube, tiktok, instagram
    account_name: Mapped[str] = mapped_column(String(300), nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    extra_data: Mapped[str | None] = mapped_column(Text)  # JSON blob for platform-specific fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


_engines: dict[str, object] = {}


def get_engine(config: AppConfig):
    url = config.database.url
    if url not in _engines:
        _engines[url] = create_engine(url, echo=False)
    return _engines[url]


def init_db(config: AppConfig):
    """Create all tables."""
    engine = get_engine(config)
    Base.metadata.create_all(engine)
    return engine


def get_session(config: AppConfig) -> Session:
    """Get a new database session."""
    engine = get_engine(config)
    return sessionmaker(bind=engine)()
