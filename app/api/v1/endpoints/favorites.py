from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....models.models import Favorite, Track, User
from ....schemas.schemas import TrackResponse
from .tracks import format_track_response
from ..deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[TrackResponse])
def get_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    favs = db.query(Favorite).filter(Favorite.user_id == current_user.id).order_by(Favorite.created_at.desc()).all()
    tracks = [f.track for f in favs if f.track]
    return [format_track_response(t, current_user.id, db) for t in tracks]

@router.post("/{track_id}/toggle")
def toggle_favorite(
    track_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    fav = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.track_id == track_id
    ).first()

    if fav:
        db.delete(fav)
        db.commit()
        return {"isFavorite": False, "message": "Removed from favorites"}
    else:
        new_fav = Favorite(user_id=current_user.id, track_id=track_id)
        db.add(new_fav)
        db.commit()
        return {"isFavorite": True, "message": "Added to favorites"}

