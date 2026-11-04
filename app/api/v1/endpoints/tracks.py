import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....core.config import settings
from ....models.models import Track, Artist, Album, AudioAsset, User, Favorite
from ....schemas.schemas import TrackResponse, TrackDetailResponse
from ....services.audio_extractor import AudioMetadataExtractor
from ....services.storage import StorageService
from ....services.streaming import stream_audio_file
from ..deps import get_current_user_optional, get_current_user

router = APIRouter()

def format_track_response(track: Track, current_user_id: Optional[str] = None, db: Optional[Session] = None) -> TrackResponse:
    is_fav = False
    if current_user_id and db:
        fav = db.query(Favorite).filter(Favorite.user_id == current_user_id, Favorite.track_id == track.id).first()
        is_fav = fav is not None

    stream_url = f"/api/v1/tracks/{track.id}/stream"

    return TrackResponse(
        id=track.id,
        title=track.title,
        artistId=track.artist_id,
        artistName=track.artist.name if track.artist else "Unknown Artist",
        albumId=track.album_id,
        albumTitle=track.album.title if track.album else None,
        coverArtUrl=track.cover_art_url or (track.album.cover_art_url if track.album else None),
        durationSeconds=track.duration_seconds,
        trackNumber=track.track_number,
        discNumber=track.disc_number,
        genre=track.genre,
        year=track.year,
        codec=track.codec,
        sampleRate=track.sample_rate,
        bitDepth=track.bit_depth,
        bitrate=track.bitrate,
        isLossless=track.is_lossless,
        isHiRes=track.is_hires,
        streamUrl=stream_url,
        isFavorite=is_fav,
        checksumSha256=track.checksum_sha256,
        createdAt=track.created_at,
    )

@router.get("", response_model=List[TrackResponse])
def get_tracks(
    genre: Optional[str] = None,
    artist_id: Optional[str] = None,
    album_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = db.query(Track)
    if genre:
        query = query.filter(Track.genre.ilike(f"%{genre}%"))
    if artist_id:
        query = query.filter(Track.artist_id == artist_id)
    if album_id:
        query = query.filter(Track.album_id == album_id)

    tracks = query.order_by(Track.created_at.desc()).limit(limit).all()
    user_id = current_user.id if isinstance(current_user, User) else None
    return [format_track_response(t, user_id, db) for t in tracks]

@router.get("/{track_id}", response_model=TrackDetailResponse)
def get_track(
    track_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    user_id = current_user.id if isinstance(current_user, User) else None
    base_res = format_track_response(track, user_id, db)
    asset = db.query(AudioAsset).filter(AudioAsset.track_id == track.id).first()

    return TrackDetailResponse(
        **base_res.model_dump(),
        fileSizeBytes=asset.file_size_bytes if asset else None,
        channels=asset.channels if asset else 2
    )

@router.get("/{track_id}/stream")
def stream_track(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    file_path = StorageService.get_audio_path(track.file_path)
    if not file_path:
        raise HTTPException(status_code=404, detail="Physical audio file not found on disk")

    return stream_audio_file(file_path, track.codec, request)

@router.get("/artwork/{filename}")
def get_artwork(filename: str):
    artwork_path = os.path.join(settings.ARTWORK_DIR, filename)
    if not os.path.exists(artwork_path):
        raise HTTPException(status_code=404, detail="Artwork not found")
    return FileResponse(artwork_path)

@router.post("/upload", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def upload_track(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    artist_name: Optional[str] = Form(None),
    album_title: Optional[str] = Form(None),
    genre: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    filename = file.filename or "track.wav"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".flac", ".wav", ".mp3", ".alac", ".aiff", ".aac", ".opus"]:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum permitted upload limit")

    # Save audio file
    saved_path = StorageService.save_audio_file(content, ext)

    # Extract audio metadata
    extracted = AudioMetadataExtractor.extract(saved_path)

    track_title = title or extracted.get("title") or os.path.splitext(filename)[0]
    final_artist_name = artist_name or extracted.get("artist") or "Unknown Artist"
    final_album_title = album_title or extracted.get("album") or "Single"
    final_genre = genre or extracted.get("genre") or "Audiophile"

    # Save embedded artwork if present
    cover_art_url = None
    if extracted.get("embedded_artwork"):
        cover_art_url = StorageService.save_artwork_file(extracted["embedded_artwork"])

    # Resolve or create Artist
    artist = db.query(Artist).filter(Artist.name.ilike(final_artist_name)).first()
    if not artist:
        artist = Artist(name=final_artist_name, genres=final_genre)
        db.add(artist)
        db.commit()
        db.refresh(artist)

    # Resolve or create Album
    album = None
    if final_album_title:
        album = db.query(Album).filter(
            Album.title.ilike(final_album_title),
            Album.artist_id == artist.id
        ).first()
        if not album:
            album = Album(
                title=final_album_title,
                artist_id=artist.id,
                cover_art_url=cover_art_url,
                genre=final_genre,
                year=extracted.get("year"),
                is_hires=extracted.get("is_hires", False),
                total_tracks=1,
                total_duration_seconds=int(extracted.get("duration_seconds", 0))
            )
            db.add(album)
            db.commit()
            db.refresh(album)

    # Create Track entity
    track = Track(
        title=track_title,
        artist_id=artist.id,
        album_id=album.id if album else None,
        duration_seconds=extracted.get("duration_seconds", 0.0),
        track_number=extracted.get("track_number", 1),
        disc_number=extracted.get("disc_number", 1),
        genre=final_genre,
        year=extracted.get("year"),
        codec=extracted.get("codec", ext.lstrip(".")),
        sample_rate=extracted.get("sample_rate", 44100),
        bit_depth=extracted.get("bit_depth", 16),
        bitrate=extracted.get("bitrate"),
        is_lossless=extracted.get("is_lossless", False),
        is_hires=extracted.get("is_hires", False),
        file_path=saved_path,
        checksum_sha256=extracted.get("checksum_sha256"),
        cover_art_url=cover_art_url or (album.cover_art_url if album else None),
        uploaded_by=current_user.id if current_user else None,
    )
    db.add(track)
    db.commit()
    db.refresh(track)

    # Create AudioAsset entity
    audio_asset = AudioAsset(
        track_id=track.id,
        storage_key=saved_path,
        file_size_bytes=len(content),
        mime_type=f"audio/{track.codec}",
        channels=extracted.get("channels", 2),
        is_original=True,
    )
    db.add(audio_asset)
    db.commit()

    return format_track_response(track, current_user.id if current_user else None, db)

@router.post("/sync-online")
def sync_online_music(
    genres: str = "ambient,jazz,classical",
    count: int = 5,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    from ....services.jamendo import JamendoCatalogService
    tracks_data = JamendoCatalogService.fetch_tracks(tags=genres, limit=count)
    if not tracks_data:
        raise HTTPException(status_code=502, detail="Unable to retrieve tracks from online catalog")

    user_id = current_user.id if isinstance(current_user, User) else None
    imported_tracks = []
    for item in tracks_data:
        t = JamendoCatalogService.ingest_track(item, db=db, user_id=user_id)
        if t:
            imported_tracks.append(format_track_response(t, user_id, db))

    return {
        "success": True,
        "count": len(imported_tracks),
        "tracks": imported_tracks,
        "message": f"Successfully synchronized {len(imported_tracks)} Creative Commons tracks from Jamendo"
    }

@router.post("/import-directory")
def import_local_directory(
    directory_path: str = Form(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        raise HTTPException(status_code=400, detail="Directory not found or is not a valid folder path")

    user_id = current_user.id if isinstance(current_user, User) else None
    supported_exts = {".flac", ".wav", ".mp3", ".alac", ".aiff", ".aac", ".opus"}

    imported_count = 0
    skipped_count = 0

    for root, _, files in os.walk(directory_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_exts:
                file_path = os.path.join(root, file)
                if db.query(Track).filter(Track.file_path == file_path).first():
                    skipped_count += 1
                    continue

                try:
                    extracted = AudioMetadataExtractor.extract(file_path)
                    cover_art_url = None
                    if extracted.get("embedded_artwork"):
                        cover_art_url = StorageService.save_artwork_file(extracted["embedded_artwork"])

                    artist_name = extracted.get("artist") or "Unknown Artist"
                    album_title = extracted.get("album") or "Single Releases"
                    genre = extracted.get("genre") or "Audiophile"

                    artist = db.query(Artist).filter(Artist.name.ilike(artist_name)).first()
                    if not artist:
                        artist = Artist(name=artist_name, genres=genre)
                        db.add(artist)
                        db.commit()
                        db.refresh(artist)

                    album = db.query(Album).filter(Album.title.ilike(album_title), Album.artist_id == artist.id).first()
                    if not album:
                        album = Album(
                            title=album_title,
                            artist_id=artist.id,
                            cover_art_url=cover_art_url,
                            genre=genre,
                            year=extracted.get("year"),
                            is_hires=extracted.get("is_hires", False),
                            total_tracks=1,
                            total_duration_seconds=int(extracted.get("duration_seconds", 0))
                        )
                        db.add(album)
                        db.commit()
                        db.refresh(album)

                    t = Track(
                        title=extracted.get("title") or os.path.splitext(file)[0],
                        artist_id=artist.id,
                        album_id=album.id,
                        duration_seconds=extracted.get("duration_seconds", 0.0),
                        track_number=extracted.get("track_number", 1),
                        disc_number=extracted.get("disc_number", 1),
                        genre=genre,
                        year=extracted.get("year"),
                        codec=extracted.get("codec", "wav"),
                        sample_rate=extracted.get("sample_rate", 44100),
                        bit_depth=extracted.get("bit_depth", 16),
                        bitrate=extracted.get("bitrate"),
                        is_lossless=extracted.get("is_lossless", False),
                        is_hires=extracted.get("is_hires", False),
                        file_path=file_path,
                        checksum_sha256=extracted.get("checksum_sha256"),
                        cover_art_url=cover_art_url or album.cover_art_url,
                        uploaded_by=user_id,
                    )
                    db.add(t)
                    db.commit()

                    asset = AudioAsset(
                        track_id=t.id,
                        storage_key=file_path,
                        file_size_bytes=os.path.getsize(file_path),
                        mime_type=f"audio/{t.codec}",
                        channels=extracted.get("channels", 2),
                        is_original=True
                    )
                    db.add(asset)
                    db.commit()
                    imported_count += 1
                except Exception:
                    db.rollback()

    return {
        "success": True,
        "imported": imported_count,
        "skipped": skipped_count,
        "message": f"Successfully imported {imported_count} audio files into NEIRO YOMI (Skipped {skipped_count} existing)"
    }

@router.get("/online/search")
def online_search(q: str = Query(..., min_length=1), limit: int = 20):
    from ....services.spotube_service import SpotubeService
    return SpotubeService.search(q, limit=limit)

@router.get("/online/trending")
def online_trending(limit: int = 15):
    from ....services.spotube_service import SpotubeService
    return SpotubeService.get_trending(limit=limit)

@router.get("/online/category/{category_name}")
def online_category(category_name: str, limit: int = 15):
    from ....services.spotube_service import SpotubeService
    return SpotubeService.get_by_category(category_name, limit=limit)

@router.post("/online-save/{video_id}")
def online_save(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Downloads and permanently ingests an online track into the user's master library.
    """
    from ....services.spotube_service import SpotubeService
    user_id = current_user.id if isinstance(current_user, User) else None
    track = SpotubeService.save_track_to_library(video_id, db=db, user_id=user_id)
    if not track:
        raise HTTPException(status_code=500, detail="Failed to download and ingest online track into library")
    return {
        "success": True,
        "message": f"Successfully added '{track.title}' to your Master Collection!",
        "track": format_track_response(track, user_id, db)
    }

@router.get("/online-stream/{video_id}")
def online_stream(video_id: str, request: Request):
    """
    Streams audio from YouTube Music / Spotube with full Range request support
    and CORS enabled for Web Audio API DSP 10-band EQ and FFT Visualizer.
    """
    import requests
    from fastapi.responses import StreamingResponse, RedirectResponse
    from ....services.spotube_service import SpotubeService

    stream_url = SpotubeService.get_audio_stream_url(video_id)
    if not stream_url:
        raise HTTPException(status_code=404, detail="Could not resolve online audio stream for track")

    # Proxy streaming with Range support for Web Audio API without CORS restrictions
    req_headers = {}
    range_header = request.headers.get("range")
    if range_header:
        req_headers["Range"] = range_header

    try:
        upstream = requests.get(stream_url, headers=req_headers, stream=True, timeout=12)
        status_code = upstream.status_code

        res_headers = {
            "Content-Type": upstream.headers.get("Content-Type", "audio/webm"),
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range",
        }
        for h in ["Content-Range", "Content-Length"]:
            if h in upstream.headers:
                res_headers[h] = upstream.headers[h]

        def iter_chunks():
            try:
                for chunk in upstream.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        return StreamingResponse(iter_chunks(), status_code=status_code, headers=res_headers)
    except Exception as e:
        # Fallback to direct redirect
        return RedirectResponse(url=stream_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
