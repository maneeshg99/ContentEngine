"""Tests for database models."""

from content_engine.config import AppConfig
from content_engine.database import (
    Clip,
    ClipStatus,
    PlatformAccount,
    Source,
    SourceStatus,
    init_db,
    get_session,
)


def test_init_db_and_create_source():
    """Test database initialization and source creation."""
    config = AppConfig(database={"url": "sqlite:///:memory:"})
    init_db(config)
    session = get_session(config)

    source = Source(
        url="https://example.com/video",
        title="Test Video",
        channel="Test Channel",
        duration=600.0,
        status=SourceStatus.DOWNLOADED,
    )
    session.add(source)
    session.commit()

    fetched = session.get(Source, source.id)
    assert fetched.title == "Test Video"
    assert fetched.status == SourceStatus.DOWNLOADED


def test_create_clip():
    config = AppConfig(database={"url": "sqlite:///:memory:"})
    init_db(config)
    session = get_session(config)

    source = Source(url="https://example.com/video", status=SourceStatus.DOWNLOADED)
    session.add(source)
    session.commit()

    clip = Clip(
        source_id=source.id,
        start_time=10.0,
        end_time=70.0,
        duration=60.0,
        status=ClipStatus.EXTRACTED,
    )
    session.add(clip)
    session.commit()

    assert clip.id is not None
    assert clip.duration == 60.0


def test_platform_account():
    config = AppConfig(database={"url": "sqlite:///:memory:"})
    init_db(config)
    session = get_session(config)

    account = PlatformAccount(
        platform="youtube",
        account_name="my-channel",
        access_token="token123",
        refresh_token="refresh456",
    )
    session.add(account)
    session.commit()

    fetched = session.get(PlatformAccount, account.id)
    assert fetched.platform == "youtube"
    assert fetched.account_name == "my-channel"
