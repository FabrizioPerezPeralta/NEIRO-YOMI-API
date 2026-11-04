from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....models.models import Artist, Track, Album, User
from ....schemas.schemas import ArtistResponse, AlbumResponse
from .tracks import format_track_response
from .albums import format_album_response
from ..deps import get_current_user_optional

router = APIRouter()

def format_artist_response(artist: Artist) -> ArtistResponse:
    genres_list = [g.strip() for g in artist.genres.split(",")] if artist.genres else []
    return ArtistResponse(
        id=artist.id,
        name=artist.name,
        biography=artist.biography,
        imageUrl=artist.image_url,
        country=artist.country,
        genres=genres_list,
        isVerified=artist.is_verified,
        createdAt=artist.created_at,
    )

@router.get("", response_model=List[ArtistResponse])
def get_artists(db: Session = Depends(get_db)):
    artists = db.query(Artist).order_by(Artist.name.asc()).all()
    return [format_artist_response(a) for a in artists]

@router.get("/{artist_id}")
def get_artist(
    artist_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    user_id = current_user.id if isinstance(current_user, User) else None
    albums = [format_album_response(a) for a in artist.albums]
    tracks = [format_track_response(t, user_id, db) for t in artist.tracks[:10]]

    artist_res = format_artist_response(artist).model_dump()
    artist_res["albums"] = albums
    artist_res["topTracks"] = tracks
    return artist_res
