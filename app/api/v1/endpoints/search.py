from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....models.models import Track, Album, Artist, User
from ....schemas.schemas import SearchResultResponse
from .tracks import format_track_response
from .albums import format_album_response
from .artists import format_artist_response
from ..deps import get_current_user_optional

router = APIRouter()

@router.get("", response_model=SearchResultResponse)
def search(
    q: str = Query("", description="Search term for tracks, albums, or artists"),
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    if not q.strip():
        return SearchResultResponse()

    search_pattern = f"%{q.strip()}%"

    # Search tracks (by title, genre, artist name, or album title)
    tracks = db.query(Track).outerjoin(Artist).outerjoin(Album).filter(
        (Track.title.ilike(search_pattern)) |
        (Track.genre.ilike(search_pattern)) |
        (Artist.name.ilike(search_pattern)) |
        (Album.title.ilike(search_pattern))
    ).limit(limit).all()

    # Search albums
    albums = db.query(Album).outerjoin(Artist).filter(
        (Album.title.ilike(search_pattern)) |
        (Album.genre.ilike(search_pattern)) |
        (Artist.name.ilike(search_pattern))
    ).limit(limit).all()

    # Search artists
    artists = db.query(Artist).filter(
        (Artist.name.ilike(search_pattern)) | (Artist.genres.ilike(search_pattern))
    ).limit(limit).all()

    user_id = current_user.id if isinstance(current_user, User) else None

    # Search global online catalog (YouTube Music / Spotube backend)
    online_results = []
    try:
        from ....services.spotube_service import SpotubeService
        online_results = SpotubeService.search(q, limit=limit)
    except Exception as e:
        print(f"[Online search fallback] {e}")

    return SearchResultResponse(
        tracks=[format_track_response(t, user_id, db) for t in tracks],
        albums=[format_album_response(a) for a in albums],
        artists=[format_artist_response(a) for a in artists],
        onlineTracks=online_results
    )
