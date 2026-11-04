from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....models.models import Album, Track, User
from ....schemas.schemas import AlbumResponse, TrackResponse
from .tracks import format_track_response
from ..deps import get_current_user_optional

router = APIRouter()

def format_album_response(album: Album) -> AlbumResponse:
    return AlbumResponse(
        id=album.id,
        title=album.title,
        artistId=album.artist_id,
        artistName=album.artist.name if album.artist else "Unknown Artist",
        coverArtUrl=album.cover_art_url,
        releaseDate=album.release_date,
        year=album.year,
        genre=album.genre,
        totalTracks=len(album.tracks) if album.tracks else album.total_tracks,
        totalDurationSeconds=sum(int(t.duration_seconds) for t in album.tracks) if album.tracks else album.total_duration_seconds,
        isHiRes=album.is_hires,
        createdAt=album.created_at,
    )

@router.get("", response_model=List[AlbumResponse])
def get_albums(db: Session = Depends(get_db)):
    albums = db.query(Album).order_by(Album.created_at.desc()).all()
    return [format_album_response(a) for a in albums]

@router.get("/{album_id}")
def get_album(
    album_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    user_id = current_user.id if isinstance(current_user, User) else None
    tracks_res = [format_track_response(t, user_id, db) for t in album.tracks]
    album_res = format_album_response(album).model_dump()
    album_res["tracks"] = tracks_res
    return album_res
