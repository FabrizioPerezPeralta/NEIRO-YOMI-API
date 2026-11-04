import os
import time
import requests
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..core.config import settings
from ..models.models import Artist, Album, Track, AudioAsset, User
from .audio_extractor import AudioMetadataExtractor
from .storage import StorageService

try:
    from ytmusicapi import YTMusic
except ImportError:
    YTMusic = None

import yt_dlp

class SpotubeService:
    """
    Spotube / ViMusic / Apple Music architecture:
    Uses YouTube Music for rich global music catalog metadata & search,
    yt-dlp for direct high-bitrate audio streaming and offline download,
    and Jamendo CC as open music fallback.
    """
    _ytmusic = None
    _stream_cache: Dict[str, Dict[str, Any]] = {}
    _search_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_ytmusic(cls):
        if cls._ytmusic is None and YTMusic is not None:
            try:
                cls._ytmusic = YTMusic()
            except Exception as e:
                print(f"[SpotubeService YTMusic Init Warning] {e}")
                cls._ytmusic = None
        return cls._ytmusic

    @classmethod
    def search(cls, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        query_key = query.strip().lower()
        now = time.time()
        # In-memory search cache (5 minutes)
        if query_key in cls._search_cache:
            cached = cls._search_cache[query_key]
            if now - cached["timestamp"] < 300:
                return cached["results"]

        tracks: List[Dict[str, Any]] = []

        # 1. Primary: Try ytmusicapi
        yt = cls.get_ytmusic()
        if yt:
            try:
                results = []
                try:
                    results = yt.search(query, filter="songs")
                except Exception:
                    pass
                if not results:
                    results = yt.search(query)

                for item in results[:limit]:
                    video_id = item.get("videoId") or item.get("id")
                    if not video_id:
                        continue

                    thumbnails = item.get("thumbnails", [])
                    cover_url = thumbnails[-1].get("url") if thumbnails else None
                    artists = item.get("artists", [])
                    artist_name = ", ".join(a.get("name", "") for a in artists) if artists else (item.get("author") or "Unknown Artist")
                    album = item.get("album")
                    album_title = album.get("name") if (isinstance(album, dict) and album) else "Single"

                    duration_raw = item.get("duration_seconds")
                    if not duration_raw and item.get("duration"):
                        parts = str(item["duration"]).split(":")
                        try:
                            duration_raw = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        except Exception:
                            duration_raw = 180
                    duration_seconds = float(duration_raw) if duration_raw else 180.0

                    tracks.append({
                        "id": f"yt_{video_id}",
                        "videoId": video_id,
                        "title": item.get("title", "Unknown Title"),
                        "artistId": f"art_{artists[0].get('id', 'unk') if artists else 'unk'}",
                        "artistName": artist_name,
                        "albumId": f"alb_{album.get('id', 'unk') if (isinstance(album, dict) and album) else 'unk'}",
                        "albumTitle": album_title,
                        "coverArtUrl": cover_url,
                        "durationSeconds": duration_seconds,
                        "codec": "opus",
                        "sampleRate": 48000,
                        "bitDepth": 16,
                        "bitrate": 160,
                        "isLossless": False,
                        "isHiRes": False,
                        "streamUrl": f"/api/v1/tracks/online-stream/{video_id}",
                        "source": "online_catalog"
                    })
            except Exception as e:
                print(f"[SpotubeService YTMusic Search fallback] {e}")

        # 2. Secondary: Fallback to yt-dlp search if ytmusicapi returned nothing
        if not tracks:
            try:
                ydl_opts = {
                    "quiet": True,
                    "extract_flat": True,
                    "skip_download": True,
                    "no_warnings": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    res = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                    entries = res.get("entries", []) if res else []
                    for entry in entries:
                        if not entry:
                            continue
                        vid = entry.get("id")
                        if not vid:
                            continue
                        tracks.append({
                            "id": f"yt_{vid}",
                            "videoId": vid,
                            "title": entry.get("title", "Unknown Title"),
                            "artistId": "art_online",
                            "artistName": entry.get("uploader") or entry.get("channel") or "Unknown Artist",
                            "albumId": "alb_online",
                            "albumTitle": "Online Release",
                            "coverArtUrl": entry.get("thumbnail") or (entry.get("thumbnails", [{}])[-1].get("url") if entry.get("thumbnails") else None),
                            "durationSeconds": float(entry.get("duration") or 180.0),
                            "codec": "opus",
                            "sampleRate": 48000,
                            "bitDepth": 16,
                            "bitrate": 160,
                            "isLossless": False,
                            "isHiRes": False,
                            "streamUrl": f"/api/v1/tracks/online-stream/{vid}",
                            "source": "online_catalog"
                        })
            except Exception as e:
                print(f"[SpotubeService yt-dlp Search fallback] {e}")

        # 3. Tertiary: Fallback to Jamendo open search
        if not tracks:
            try:
                from .jamendo import JamendoCatalogService
                jam_tracks = JamendoCatalogService.fetch_tracks(search_query=query, limit=limit)
                if not jam_tracks:
                    jam_tracks = JamendoCatalogService.fetch_tracks(tags=query, limit=limit)
                for jt in jam_tracks:
                    tracks.append({
                        "id": f"jam_{jt.get('id')}",
                        "videoId": f"jam_{jt.get('id')}",
                        "title": jt.get("name"),
                        "artistId": f"art_jam_{jt.get('artist_id')}",
                        "artistName": jt.get("artist_name"),
                        "albumId": f"alb_jam_{jt.get('album_id')}",
                        "albumTitle": jt.get("album_name") or "Creative Commons",
                        "coverArtUrl": jt.get("image"),
                        "durationSeconds": float(jt.get("duration", 180)),
                        "codec": "mp3",
                        "sampleRate": 44100,
                        "bitDepth": 16,
                        "bitrate": 320,
                        "isLossless": False,
                        "isHiRes": False,
                        "streamUrl": jt.get("audio"),
                        "source": "online_catalog"
                    })
            except Exception as e:
                print(f"[SpotubeService Jamendo Search fallback] {e}")

        cls._search_cache[query_key] = {"results": tracks, "timestamp": now}
        return tracks

    @classmethod
    def get_audio_stream_url(cls, video_id: str) -> Optional[str]:
        now = time.time()
        # In-memory cache valid for 1 hour
        if video_id in cls._stream_cache:
            cached = cls._stream_cache[video_id]
            if now - cached["timestamp"] < 3600:
                return cached["url"]

        # Jamendo direct audio URL
        if video_id.startswith("jam_"):
            return None

        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get("url")
                if stream_url:
                    cls._stream_cache[video_id] = {
                        "url": stream_url,
                        "timestamp": now,
                        "codec": info.get("acodec", "opus")
                    }
                    return stream_url
        except Exception as e:
            print(f"[SpotubeService Stream Error for {video_id}] {e}")

        return None

    @classmethod
    def get_trending(cls, limit: int = 15) -> List[Dict[str, Any]]:
        return cls.search("Top Hits 2026 Today's Top Hits Billboard", limit=limit)

    @classmethod
    def get_by_category(cls, category: str, limit: int = 15) -> List[Dict[str, Any]]:
        category_queries = {
            "city_pop": "Japanese City Pop 80s 90s Tatsuro Yamashita Mariya Takeuchi",
            "lofi": "Lofi hip hop chill beats study relax",
            "jazz": "Audiophile Jazz trio acoustic piano saxophone",
            "classical": "Classical masterpieces orchestra piano Chopin Beethoven",
            "rock": "Classic Rock legends Queen Pink Floyd Led Zeppelin",
            "electronic": "Electronic synthwave retrowave Daft Punk",
        }
        query = category_queries.get(category.lower(), category)
        return cls.search(query, limit=limit)

    @classmethod
    def save_track_to_library(cls, video_id: str, db: Session, user_id: Optional[str] = None) -> Optional[Track]:
        """
        One-click Save to Library (Spotify / Apple Music offline style):
        Downloads high quality audio stream and artwork, indexes into local database.
        """
        # If already in database by videoId
        existing_track = db.query(Track).filter(Track.checksum_sha256 == f"yt_{video_id}").first()
        if existing_track:
            return existing_track

        url = f"https://www.youtube.com/watch?v={video_id}"
        out_tmpl = os.path.join(settings.AUDIO_DIR, f"{video_id}.%(ext)s")

        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": out_tmpl,
            "quiet": True,
            "no_warnings": True,
            "writethumbnail": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)

                if not os.path.exists(downloaded_file):
                    # Check matching extension
                    base_prefix = os.path.join(settings.AUDIO_DIR, video_id)
                    for ext in [".m4a", ".opus", ".webm", ".mp3", ".ogg"]:
                        if os.path.exists(base_prefix + ext):
                            downloaded_file = base_prefix + ext
                            break

                if not os.path.exists(downloaded_file):
                    return None

                title = info.get("title") or f"Track {video_id}"
                artist_name = info.get("artist") or info.get("uploader") or "Online Artist"
                album_title = info.get("album") or f"{title} - Single"
                duration = float(info.get("duration") or 180.0)
                thumbnail_url = info.get("thumbnail")

                # Save cover artwork locally
                cover_art_url = None
                if thumbnail_url:
                    try:
                        thumb_resp = requests.get(thumbnail_url, timeout=10)
                        if thumb_resp.status_code == 200:
                            cover_art_url = StorageService.save_artwork_file(thumb_resp.content, filename=f"yt_{video_id}.jpg")
                    except Exception:
                        pass

                # Artist
                artist = db.query(Artist).filter(Artist.name.ilike(artist_name)).first()
                if not artist:
                    artist = Artist(name=artist_name, genres="Streaming")
                    db.add(artist)
                    db.commit()
                    db.refresh(artist)

                # Album
                album = db.query(Album).filter(Album.title.ilike(album_title), Album.artist_id == artist.id).first()
                if not album:
                    album = Album(
                        title=album_title,
                        artist_id=artist.id,
                        cover_art_url=cover_art_url,
                        genre="Streaming",
                        total_tracks=1,
                        total_duration_seconds=int(duration)
                    )
                    db.add(album)
                    db.commit()
                    db.refresh(album)

                # Extract audio properties
                try:
                    meta = AudioMetadataExtractor.extract(downloaded_file)
                    codec = meta.get("codec", os.path.splitext(downloaded_file)[1].lstrip("."))
                    sample_rate = meta.get("sample_rate", 48000)
                    bit_depth = meta.get("bit_depth", 16)
                    is_lossless = meta.get("is_lossless", False)
                except Exception:
                    codec = os.path.splitext(downloaded_file)[1].lstrip(".")
                    sample_rate = 48000
                    bit_depth = 16
                    is_lossless = False

                # Track
                track = Track(
                    title=title,
                    artist_id=artist.id,
                    album_id=album.id,
                    duration_seconds=duration,
                    track_number=1,
                    genre="Streaming",
                    codec=codec,
                    sample_rate=sample_rate,
                    bit_depth=bit_depth,
                    bitrate=160,
                    is_lossless=is_lossless,
                    is_hires=False,
                    file_path=downloaded_file,
                    checksum_sha256=f"yt_{video_id}",
                    cover_art_url=cover_art_url or album.cover_art_url,
                    uploaded_by=user_id,
                )
                db.add(track)
                db.commit()
                db.refresh(track)

                # Audio Asset
                file_size = os.path.getsize(downloaded_file)
                asset = AudioAsset(
                    track_id=track.id,
                    storage_key=downloaded_file,
                    file_size_bytes=file_size,
                    mime_type=f"audio/{codec}",
                    channels=2,
                    is_original=True
                )
                db.add(asset)
                db.commit()

                return track

        except Exception as e:
            print(f"[SpotubeService Save Track Error] {e}")
            db.rollback()
            return None


