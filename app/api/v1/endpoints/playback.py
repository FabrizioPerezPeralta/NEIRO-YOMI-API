from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....models.models import PlaybackSession, Track, User, ListeningHistory
from ....schemas.schemas import PlaybackSessionCreate, PlaybackSessionResponse, PlaybackHeartbeatRequest
from ..deps import get_current_user

router = APIRouter()

@router.post("/sessions", response_model=PlaybackSessionResponse)
def create_or_resume_session(
    req: PlaybackSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    track = db.query(Track).filter(Track.id == req.trackId).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    session = db.query(PlaybackSession).filter(
        PlaybackSession.user_id == current_user.id,
        PlaybackSession.device_id == req.deviceId
    ).first()

    if not session:
        session = PlaybackSession(
            user_id=current_user.id,
            device_id=req.deviceId,
            track_id=req.trackId,
            position_seconds=0.0,
            is_playing=True
        )
        db.add(session)
    else:
        session.track_id = req.trackId
        session.is_playing = True
        session.updated_at = datetime.now(timezone.utc)

    # Record listening history entry
    history = ListeningHistory(
        user_id=current_user.id,
        track_id=req.trackId,
        completion_ratio=0.0
    )
    db.add(history)

    db.commit()
    db.refresh(session)

    return PlaybackSessionResponse(
        sessionId=session.id,
        userId=session.user_id,
        deviceId=session.device_id,
        trackId=session.track_id,
        positionSeconds=session.position_seconds,
        isPlaying=session.is_playing,
        updatedAt=session.updated_at
    )

@router.post("/sessions/{session_id}/heartbeat")
def session_heartbeat(
    session_id: str,
    req: PlaybackHeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(PlaybackSession).filter(
        PlaybackSession.id == session_id,
        PlaybackSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Playback session not found")

    session.position_seconds = req.positionSeconds
    session.is_playing = req.isPlaying
    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok", "positionSeconds": session.position_seconds}

