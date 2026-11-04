import os
import requests
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..core.config import settings
from ..models.models import Artist, Album, Track, AudioAsset, License, User
from .storage import StorageService

JAMENDO_CLIENT_ID = os.getenv("JAMENDO_CLIENT_ID", "56d30c95")  # Free public API client ID for Jamendo CC music
JAMENDO_API_URL = "https://api.jamendo.com/v3.0/tracks/"

class JamendoCatalogService:
    """
    Ingests legally licensed Creative Commons audio from Jamendo API
    into the NEIRO YOMI catalog as specified in README.md Section 12.
    """

    @classmethod
    def fetch_tracks(
        cls,
        tags: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 10,
        audio_format: str = "mp32"  # 320kbps MP3
    ) -> List[Dict[str, Any]]:
        params = {
            "client_id": JAMENDO_CLIENT_ID,
            "format": "json",
            "limit": limit,
            "audioformat": audio_format,
            "include": "musicinfo,licenses",
            "order": "popularity_total",
        }
        if search_query:
            params["namesearch"] = search_query
        elif tags:
            params["tags"] = tags

        try:
            resp = requests.get(JAMENDO_API_URL, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])
        except Exception as e:
            print(f"[Jamendo API Error] {e}")

        return []

    @classmethod
    def ingest_track(cls, track_data: Dict[str, Any], db: Session, user_id: Optional[str] = None) -> Optional[Track]:
        track_title = track_data.get("name")
        artist_name = track_data.get("artist_name", "Independent Artist")
        album_title = track_data.get("album_name") or f"{track_title} - Single"
        audio_url = track_data.get("audio")
        cover_image_url = track_data.get("image")
        duration = float(track_data.get("duration", 180))
        license_url = track_data.get("license_ccurl", "https://creativecommons.org/licenses/by-sa/4.0/")

        if not audio_url or not track_title:
            return None

        # Check if already in database
        existing = db.query(Track).filter(
            Track.title == track_title,
            Track.duration_seconds == duration
        ).first()
        if existing:
            return existing

        # Download audio stream to storage so it plays offline & bit-accurately
        try:
            audio_resp = requests.get(audio_url, timeout=30, stream=True)
            if audio_resp.status_code != 200:
                return None
            audio_content = audio_resp.content
        except Exception as e:
            print(f"[Download Error for {track_title}] {e}")
            return None

        # Save audio file
        saved_file_path = StorageService.save_audio_file(audio_content, "mp3")

        # Artist
        artist = db.query(Artist).filter(Artist.name.ilike(artist_name)).first()
        if not artist:
            artist = Artist(
                name=artist_name,
                image_url=track_data.get("artist_image"),
                genres=track_data.get("musicinfo", {}).get("tags", {}).get("genres", ["Audiophile"])[0] if track_data.get("musicinfo") else "Audiophile",
                is_verified=True
            )
            db.add(artist)
            db.commit()
            db.refresh(artist)

        # Album
        album = db.query(Album).filter(Album.title.ilike(album_title), Album.artist_id == artist.id).first()
        if not album:
            album = Album(
                title=album_title,
                artist_id=artist.id,
                cover_art_url=cover_image_url,
                genre=artist.genres,
                total_tracks=1,
                total_duration_seconds=int(duration),
                is_hires=False
            )
            db.add(album)
            db.commit()
            db.refresh(album)

        # Track
        track = Track(
            title=track_title,
            artist_id=artist.id,
            album_id=album.id,
            duration_seconds=duration,
            track_number=1,
            disc_number=1,
            genre=album.genre,
            codec="mp3",
            sample_rate=44100,
            bit_depth=16,
            bitrate=320,
            is_lossless=False,
            is_hires=False,
            file_path=saved_file_path,
            cover_art_url=cover_image_url,
            uploaded_by=user_id,
        )
        db.add(track)
        db.commit()
        db.refresh(track)

        # AudioAsset
        asset = AudioAsset(
            track_id=track.id,
            storage_key=saved_file_path,
            file_size_bytes=len(audio_content),
            mime_type="audio/mpeg",
            channels=2,
            is_original=True
        )
        db.add(asset)

        # License record
        license_entry = License(
            track_id=track.id,
            license_type="creative_commons",
            rights_holder=artist_name,
            territory="worldwide",
            is_active=True
        )
        db.add(license_entry)
        db.commit()

        return track

