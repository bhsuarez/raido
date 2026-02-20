from typing import List, Optional
import asyncio
import functools
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, or_
import structlog
import httpx

from app.core.database import get_db
from app.models import Track
from app.schemas.track import TrackRead, TrackUpdate, MBCandidate, TrackFacets

router = APIRouter()
logger = structlog.get_logger()


@router.get("/facets", response_model=TrackFacets)
async def get_track_facets(db: AsyncSession = Depends(get_db)):
    """Return distinct genres, artists, and albums for sidebar filters."""
    genres_result = await db.execute(
        select(distinct(Track.genre)).where(Track.genre.isnot(None)).order_by(Track.genre)
    )
    artists_result = await db.execute(
        select(distinct(Track.artist)).order_by(Track.artist)
    )
    albums_result = await db.execute(
        select(distinct(Track.album)).where(Track.album.isnot(None)).order_by(Track.album)
    )
    return TrackFacets(
        genres=[r[0] for r in genres_result.all()],
        artists=[r[0] for r in artists_result.all()],
        albums=[r[0] for r in albums_result.all()],
    )


@router.get("/", response_model=List[TrackRead])
async def list_tracks(
    response: Response,
    search: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    artist: Optional[str] = Query(None),
    album: Optional[str] = Query(None),
    sort: Optional[str] = Query("artist", regex="^(artist|album|title|play_count)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    no_artwork: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """List tracks with optional filtering, sorting, and pagination."""
    q = select(Track)
    count_q = select(func.count(Track.id))

    if search:
        term = f"%{search}%"
        cond = or_(
            Track.title.ilike(term),
            Track.artist.ilike(term),
            Track.album.ilike(term),
        )
        q = q.where(cond)
        count_q = count_q.where(cond)
    if genre:
        q = q.where(Track.genre == genre)
        count_q = count_q.where(Track.genre == genre)
    if artist:
        q = q.where(Track.artist == artist)
        count_q = count_q.where(Track.artist == artist)
    if album:
        q = q.where(Track.album == album)
        count_q = count_q.where(Track.album == album)
    if no_artwork:
        cond = (Track.artwork_url.is_(None)) | (Track.artwork_url == '')
        q = q.where(cond)
        count_q = count_q.where(cond)

    total = (await db.execute(count_q)).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    sort_col = {
        "artist": Track.artist,
        "album": Track.album,
        "title": Track.title,
        "play_count": Track.play_count.desc(),
    }.get(sort, Track.artist)

    if sort == "play_count":
        q = q.order_by(Track.play_count.desc())
    else:
        q = q.order_by(sort_col)

    offset = (page - 1) * per_page
    q = q.offset(offset).limit(per_page)

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{track_id}", response_model=TrackRead)
async def get_track(track_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track




_NON_GENRE_TAGS = {
    "animal on cover", "dog on cover", "cat on cover", "energetic", "playful",
    "melancholic", "uplifting", "eclectic", "melodic", "sarcastic", "satirical",
    "quirky", "urban", "aggressive", "dark", "romantic", "happy", "sad",
    "instrumental", "live", "compilation", "reissue", "remixed",
}

def _top_genre_from_tags(tags: list) -> Optional[str]:
    filtered = [t for t in tags if t.get("name", "").lower() not in _NON_GENRE_TAGS]
    if not filtered:
        return None
    top = max(filtered, key=lambda t: int(t.get("count", 0)))
    return top["name"].title()

def _sync_mb_search(artist: str, title: str) -> dict:
    """Synchronous MusicBrainz search — run in executor to avoid blocking the event loop."""
    import musicbrainzngs
    musicbrainzngs.set_useragent("Raido", "1.0", "raido@bhsuarez.com")
    return musicbrainzngs.search_recordings(artist=artist, recording=title, limit=5)


@router.get("/{track_id}/musicbrainz", response_model=List[MBCandidate])
async def search_musicbrainz(track_id: int, db: AsyncSession = Depends(get_db)):
    """Search MusicBrainz for metadata candidates for this track."""
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    try:
        loop = asyncio.get_event_loop()
        mb_result = await loop.run_in_executor(
            None,
            functools.partial(_sync_mb_search, track.artist, track.title)
        )
    except Exception as e:
        logger.warning("MusicBrainz search failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"MusicBrainz search failed: {e}")

    candidates: List[MBCandidate] = []
    seen_mbids = set()

    for rec in mb_result.get("recording-list", []) or []:
        recording_mbid = rec.get("id")
        if not recording_mbid or recording_mbid in seen_mbids:
            continue
        seen_mbids.add(recording_mbid)

        title = rec.get("title", track.title)
        artist = (rec.get("artist-credit-phrase") or "").strip() or track.artist

        release_list = rec.get("release-list", []) or []
        release = release_list[0] if release_list else {}
        release_mbid = release.get("id")
        album = release.get("title")
        country = release.get("country")

        year = None
        date_str = release.get("date", "")
        if date_str and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
            except ValueError:
                pass

        label = None
        label_info = release.get("label-info-list", [])
        if label_info and isinstance(label_info, list) and label_info[0]:
            label_entry = label_info[0].get("label", {})
            if label_entry:
                label = label_entry.get("name")

        artwork_url = None
        if release_mbid:
            caa_url = f"https://coverartarchive.org/release/{release_mbid}/front-500"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(caa_url, follow_redirects=True)
                    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                        artwork_url = str(resp.url)
            except Exception:
                pass

        candidates.append(MBCandidate(
            recording_mbid=recording_mbid,
            release_mbid=release_mbid,
            title=title,
            artist=artist,
            album=album,
            year=year,
            country=country,
            label=label,
            artwork_url=artwork_url,
        ))

    # Fetch genre from first release's tags via MB REST API (one async call)
    genre = None
    first_mbid = next((c.release_mbid for c in candidates if c.release_mbid), None)
    if first_mbid:
        try:
            async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": "Raido/1.0 (raido@bhsuarez.com)"}) as client:
                resp = await client.get(
                    f"https://musicbrainz.org/ws/2/release/{first_mbid}",
                    params={"inc": "tags release-groups", "fmt": "json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    all_tags = data.get("tags", []) + data.get("release-group", {}).get("tags", [])
                    genre = _top_genre_from_tags(all_tags)
        except Exception:
            pass

    if genre:
        for c in candidates:
            c.genre = genre

    return candidates



def _sync_mb_release_lookup(release_mbid: str, track_title: str) -> dict:
    """Look up a specific release by MBID and find the matching recording."""
    import musicbrainzngs
    musicbrainzngs.set_useragent("Raido", "1.0", "raido@bhsuarez.com")
    release = musicbrainzngs.get_release_by_id(
        release_mbid,
        includes=["artists", "recordings", "labels", "release-groups", "tags"],
    )["release"]

    artist = (release.get("artist-credit-phrase") or "").strip()

    album = release.get("title", "")
    country = release.get("country")

    date_str = release.get("date", "")
    year = None
    if date_str and len(date_str) >= 4:
        try:
            year = int(date_str[:4])
        except ValueError:
            pass

    label = None
    label_list = release.get("label-info-list", [])
    if label_list:
        label = label_list[0].get("label", {}).get("name")

    # Extract top genre from release-group tags (highest vote count, skip non-genre descriptors)
    _non_genre = {"animal on cover", "dog on cover", "cat on cover", "energetic", "playful",
                  "melancholic", "uplifting", "eclectic", "melodic", "sarcastic", "satirical",
                  "quirky", "urban", "aggressive", "dark", "romantic"}
    rg = release.get("release-group", {})
    all_tags = rg.get("tag-list", []) + release.get("tag-list", [])
    genre = None
    if all_tags:
        filtered = [t for t in all_tags if t.get("name", "").lower() not in _non_genre]
        if filtered:
            top = max(filtered, key=lambda t: int(t.get("count", 0)))
            genre = top["name"].title()

    # Find best matching track by title
    recording_mbid = None
    best_score = -1
    title_lower = track_title.lower()
    matched_track_artist = None
    for medium in release.get("medium-list", []):
        for track in medium.get("track-list", []):
            rec = track.get("recording", {})
            rec_title = rec.get("title", "").lower()
            # Simple score: exact > startswith > contains
            if rec_title == title_lower:
                score = 3
            elif rec_title.startswith(title_lower) or title_lower.startswith(rec_title):
                score = 2
            elif title_lower in rec_title or rec_title in title_lower:
                score = 1
            else:
                score = 0
            if score > best_score:
                best_score = score
                recording_mbid = rec.get("id")
                matched_track_artist = (
                    track.get("artist-credit-phrase")
                    or rec.get("artist-credit-phrase")
                    or None
                )

    # CAA artwork
    artwork_url = None
    caa = release.get("cover-art-archive", {})
    if caa.get("front") == "true" or caa.get("artwork") == "true":
        artwork_url = f"https://coverartarchive.org/release/{release_mbid}/front-500"

    if matched_track_artist:
        artist = matched_track_artist

    return {
        "recording_mbid": recording_mbid,
        "release_mbid": release_mbid,
        "artist": artist,
        "album": album,
        "year": year,
        "country": country,
        "label": label,
        "artwork_url": artwork_url,
        "genre": genre,
    }


@router.get("/{track_id}/musicbrainz/release/{release_mbid}", response_model=MBCandidate)
async def lookup_mb_release(
    track_id: int,
    release_mbid: str,
    db: AsyncSession = Depends(get_db),
):
    """Look up a specific MusicBrainz release by MBID and match the recording."""
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            functools.partial(_sync_mb_release_lookup, release_mbid, track.title),
        )
    except Exception as e:
        logger.warning("MusicBrainz release lookup failed", mbid=release_mbid, error=str(e))
        raise HTTPException(status_code=502, detail=f"MusicBrainz lookup failed: {e}")

    recording_mbid = data.get("recording_mbid")
    if not recording_mbid:
        # Return without a recording MBID if no track matched — still useful for album metadata
        recording_mbid = f"release-only-{release_mbid}"

    return MBCandidate(
        recording_mbid=recording_mbid,
        release_mbid=data["release_mbid"],
        title=track.title,
        artist=data["artist"],
        album=data["album"],
        year=data["year"],
        country=data["country"],
        label=data["label"],
        artwork_url=data["artwork_url"],
        genre=data.get("genre"),
    )


@router.patch("/{track_id}", response_model=TrackRead)
async def update_track(
    track_id: int,
    payload: TrackUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update track metadata in DB and write back to audio file tags."""
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(track, field, value)

    # Write tags back to file on disk
    file_path = track.file_path
    if file_path and not file_path.startswith("liquidsoap://"):
        try:
            _write_file_tags(file_path, update_data)
        except Exception as e:
            logger.warning("Failed to write file tags", file_path=file_path, error=str(e))

    await db.commit()
    await db.refresh(track)
    return track


def _write_file_tags(file_path: str, data: dict) -> None:
    """Write metadata tags to audio file using mutagen."""
    import os
    if not os.path.exists(file_path):
        return

    lower = file_path.lower()

    if lower.endswith(".mp3"):
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON
        try:
            tags = ID3(file_path)
        except Exception:
            from mutagen.id3 import ID3NoHeaderError
            tags = ID3()

        if "title" in data and data["title"]:
            tags["TIT2"] = TIT2(encoding=3, text=data["title"])
        if "artist" in data and data["artist"]:
            tags["TPE1"] = TPE1(encoding=3, text=data["artist"])
        if "album" in data and data["album"]:
            tags["TALB"] = TALB(encoding=3, text=data["album"])
        if "year" in data and data["year"]:
            tags["TDRC"] = TDRC(encoding=3, text=str(data["year"]))
        if "genre" in data and data["genre"]:
            tags["TCON"] = TCON(encoding=3, text=data["genre"])
        tags.save(file_path)

    elif lower.endswith(".flac"):
        from mutagen.flac import FLAC
        tags = FLAC(file_path)
        if "title" in data and data["title"]:
            tags["TITLE"] = [data["title"]]
        if "artist" in data and data["artist"]:
            tags["ARTIST"] = [data["artist"]]
        if "album" in data and data["album"]:
            tags["ALBUM"] = [data["album"]]
        if "year" in data and data["year"]:
            tags["DATE"] = [str(data["year"])]
        if "genre" in data and data["genre"]:
            tags["GENRE"] = [data["genre"]]
        tags.save()

    elif lower.endswith(".m4a") or lower.endswith(".aac"):
        from mutagen.mp4 import MP4
        tags = MP4(file_path)
        if "title" in data and data["title"]:
            tags["\xa9nam"] = [data["title"]]
        if "artist" in data and data["artist"]:
            tags["\xa9ART"] = [data["artist"]]
        if "album" in data and data["album"]:
            tags["\xa9alb"] = [data["album"]]
        if "year" in data and data["year"]:
            tags["\xa9day"] = [str(data["year"])]
        if "genre" in data and data["genre"]:
            tags["\xa9gen"] = [data["genre"]]
        tags.save()
