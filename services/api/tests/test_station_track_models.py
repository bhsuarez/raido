from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Temporarily disable loading the project's .env to avoid validation errors
_env_renamed = False
if Path(".env").exists():
    Path(".env").rename(".env.bak")
    _env_renamed = True

from app.core.database import Base  # noqa: E402
from app.models import Station, Track  # noqa: E402

if _env_renamed:
    Path(".env.bak").rename(".env")


def test_station_track_relationship():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        track = Track(title="Song", artist="Artist", file_path="/tmp/song.mp3")
        station = Station(
            name="Test Station",
            slug="test-station",
            stream_mount="/test.mp3",
            stream_name="Test Stream",
        )
        station.tracks.append(track)
        session.add(station)
        session.commit()
        session.refresh(station)
        session.refresh(track)

        assert station.tracks[0].title == "Song"
        assert track.stations[0].name == "Test Station"
        assert track.stations[0].stream_mount == "/test.mp3"
        assert track.stations[0].stream_name == "Test Stream"
