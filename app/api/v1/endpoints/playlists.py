from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....models.models import Playlist, PlaylistTrack, Track, User
from ....schemas.schemas import PlaylistCreate, PlaylistUpdate, PlaylistResponse, PlaylistTrackAddRequest, TrackResponse
from .tracks import format_track_response
from ..deps import get_current_user, get_current_user_optional

router = APIRouter()

def format_playlist_response(playlist: Playlist, current_user_id: Optional[str] = None, db: Optional[Session] = None, include_tracks: bool = False) -> PlaylistResponse:
    tracks: Optional[List[TrackResponse]] = None
    if include_tracks:
        track_models = [pt.track for pt in playlist.playlist_tracks if pt.track]
        tracks = [format_track_response(t, current_user_id, db) for t in track_models]

    duration = sum(int(pt.track.duration_seconds) for pt in playlist.playlist_tracks if pt.track)

    return PlaylistResponse(
        id=playlist.id,
        title=playlist.title,
        description=playlist.description,
        coverArtUrl=playlist.cover_art_url,
        userId=playlist.user_id,
        userName=playlist.user.display_name if playlist.user else "User",
        isPublic=playlist.is_public,
        trackCount=len(playlist.playlist_tracks),
        totalDurationSeconds=duration,
        createdAt=playlist.created_at,
        updatedAt=playlist.updated_at,
        tracks=tracks,
    )

@router.get("", response_model=List[PlaylistResponse])
def get_playlists(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = db.query(Playlist)
    if current_user:
        query = query.filter((Playlist.is_public == True) | (Playlist.user_id == current_user.id))
    else:
        query = query.filter(Playlist.is_public == True)

    playlists = query.order_by(Playlist.updated_at.desc()).all()
    user_id = current_user.id if isinstance(current_user, User) else None
    return [format_playlist_response(p, user_id, db, include_tracks=False) for p in playlists]

@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_playlist(
    req: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = Playlist(
        title=req.title,
        description=req.description,
        user_id=current_user.id,
        is_public=req.isPublic
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return format_playlist_response(playlist, current_user.id, db, include_tracks=False)

@router.get("/{playlist_id}", response_model=PlaylistResponse)
def get_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    user_id = current_user.id if isinstance(current_user, User) else None
    return format_playlist_response(playlist, user_id, db, include_tracks=True)

@router.post("/{playlist_id}/tracks")
def add_track_to_playlist(
    playlist_id: str,
    req: PlaylistTrackAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this playlist")

    track = db.query(Track).filter(Track.id == req.trackId).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    position = len(playlist.playlist_tracks)
    pt = PlaylistTrack(
        playlist_id=playlist.id,
        track_id=track.id,
        position=position
    )
    db.add(pt)
    db.commit()
    return {"success": True, "message": "Track added to playlist"}

@router.delete("/{playlist_id}/tracks/{track_id}")
def remove_track_from_playlist(
    playlist_id: str,
    track_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this playlist")

    pt = db.query(PlaylistTrack).filter(
        PlaylistTrack.playlist_id == playlist.id,
        PlaylistTrack.track_id == track_id
    ).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Track not found in playlist")

    db.delete(pt)
    db.commit()
    return {"success": True, "message": "Track removed from playlist"}
