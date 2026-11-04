import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(150), nullable=True)
    role = Column(String(50), default="user") # user, admin, artist
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    history = relationship("ListeningHistory", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Artist(Base):
    __tablename__ = "artists"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), index=True, nullable=False)
    biography = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    country = Column(String(100), nullable=True)
    genres = Column(String(255), nullable=True) # Comma-separated
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    albums = relationship("Album", back_populates="artist")
    tracks = relationship("Track", back_populates="artist")

class Album(Base):
    __tablename__ = "albums"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), index=True, nullable=False)
    artist_id = Column(String(36), ForeignKey("artists.id"), nullable=False)
    cover_art_url = Column(String(500), nullable=True)
    release_date = Column(String(50), nullable=True)
    year = Column(Integer, nullable=True)
    genre = Column(String(100), nullable=True)
    total_tracks = Column(Integer, default=0)
    total_duration_seconds = Column(Integer, default=0)
    is_hires = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    artist = relationship("Artist", back_populates="albums")
    tracks = relationship("Track", back_populates="album", cascade="all, delete-orphan")

class Track(Base):
    __tablename__ = "tracks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), index=True, nullable=False)
    artist_id = Column(String(36), ForeignKey("artists.id"), nullable=False)
    album_id = Column(String(36), ForeignKey("albums.id"), nullable=True)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    track_number = Column(Integer, nullable=True)
    disc_number = Column(Integer, default=1)
    genre = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)

    # Technical Audiophile Metadata
    codec = Column(String(50), nullable=False) # flac, alac, wav, aiff, mp3, aac, opus
    sample_rate = Column(Integer, nullable=False) # e.g. 44100, 96000, 192000
    bit_depth = Column(Integer, nullable=True) # e.g. 16, 24, 32
    bitrate = Column(Integer, nullable=True) # kbps
    is_lossless = Column(Boolean, default=False)
    is_hires = Column(Boolean, default=False)
    file_path = Column(String(500), nullable=False)
    checksum_sha256 = Column(String(64), nullable=True)
    cover_art_url = Column(String(500), nullable=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    artist = relationship("Artist", back_populates="tracks")
    album = relationship("Album", back_populates="tracks")
    audio_assets = relationship("AudioAsset", back_populates="track", cascade="all, delete-orphan")
    playlist_tracks = relationship("PlaylistTrack", back_populates="track", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="track", cascade="all, delete-orphan")
    licenses = relationship("License", back_populates="track", cascade="all, delete-orphan")

class AudioAsset(Base):
    __tablename__ = "audio_assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    track_id = Column(String(36), ForeignKey("tracks.id"), nullable=False)
    storage_key = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    channels = Column(Integer, default=2)
    is_original = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    track = relationship("Track", back_populates="audio_assets")

class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    cover_art_url = Column(String(500), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="playlists")
    playlist_tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistTrack.position")

class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    playlist_id = Column(String(36), ForeignKey("playlists.id"), nullable=False)
    track_id = Column(String(36), ForeignKey("tracks.id"), nullable=False)
    position = Column(Integer, default=0)
    added_at = Column(DateTime, default=utc_now)

    playlist = relationship("Playlist", back_populates="playlist_tracks")
    track = relationship("Track", back_populates="playlist_tracks")

class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    track_id = Column(String(36), ForeignKey("tracks.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="favorites")
    track = relationship("Track", back_populates="favorites")

class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    track_id = Column(String(36), ForeignKey("tracks.id"), nullable=False)
    played_at = Column(DateTime, default=utc_now)
    completion_ratio = Column(Float, default=1.0) # 0.0 - 1.0

    user = relationship("User", back_populates="history")
    track = relationship("Track")

class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    device_name = Column(String(255), nullable=False)
    device_type = Column(String(50), default="web") # web, desktop, mobile
    last_active_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="devices")

class PlaybackSession(Base):
    __tablename__ = "playback_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    device_id = Column(String(100), nullable=False)
    track_id = Column(String(36), ForeignKey("tracks.id"), nullable=False)
    position_seconds = Column(Float, default=0.0)
    is_playing = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User")
    track = relationship("Track")

class License(Base):
    __tablename__ = "licenses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    track_id = Column(String(36), ForeignKey("tracks.id"), nullable=False)
    license_type = Column(String(100), default="personal_locker") # personal_locker, creative_commons, direct_artist, public_domain
    rights_holder = Column(String(255), nullable=True)
    territory = Column(String(100), default="worldwide")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    track = relationship("Track", back_populates="licenses")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    preferred_quality = Column(String(50), default="lossless") # standard, high_quality, lossless, hi_res
    equalizer_preset = Column(String(50), default="flat")
    dark_mode = Column(Boolean, default=True)
    crossfade_seconds = Column(Float, default=0.0)

    user = relationship("User", back_populates="preferences")

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    status = Column(String(50), default="pending") # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User")

