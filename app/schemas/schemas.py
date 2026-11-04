from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# ------------------------------------------------------------------------------
# Auth & User Schemas
# ------------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    displayName: Optional[str] = None

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    displayName: Optional[str] = None
    role: str
    avatarUrl: Optional[str] = None
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)

class AuthResponse(BaseModel):
    user: UserResponse
    accessToken: str
    tokenType: str = "bearer"

# ------------------------------------------------------------------------------
# Artist Schemas
# ------------------------------------------------------------------------------
class ArtistResponse(BaseModel):
    id: str
    name: str
    biography: Optional[str] = None
    imageUrl: Optional[str] = None
    country: Optional[str] = None
    genres: List[str] = []
    isVerified: bool = False
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)

# ------------------------------------------------------------------------------
# Album Schemas
# ------------------------------------------------------------------------------
class AlbumResponse(BaseModel):
    id: str
    title: str
    artistId: str
    artistName: str
    coverArtUrl: Optional[str] = None
    releaseDate: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    totalTracks: int = 0
    totalDurationSeconds: int = 0
    isHiRes: bool = False
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)

# ------------------------------------------------------------------------------
# Track Schemas
# ------------------------------------------------------------------------------
class TrackResponse(BaseModel):
    id: str
    title: str
    artistId: str
    artistName: str
    albumId: Optional[str] = None
    albumTitle: Optional[str] = None
    coverArtUrl: Optional[str] = None
    durationSeconds: float
    trackNumber: Optional[int] = None
    discNumber: Optional[int] = 1
    genre: Optional[str] = None
    year: Optional[int] = None
    codec: str
    sampleRate: int
    bitDepth: Optional[int] = None
    bitrate: Optional[int] = None
    isLossless: bool
    isHiRes: bool
    streamUrl: str
    isFavorite: Optional[bool] = False
    checksumSha256: Optional[str] = None
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)

class TrackDetailResponse(TrackResponse):
    fileSizeBytes: Optional[int] = None
    channels: Optional[int] = 2

# ------------------------------------------------------------------------------
# Playlist Schemas
# ------------------------------------------------------------------------------
class PlaylistCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    isPublic: bool = False

class PlaylistUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    isPublic: Optional[bool] = None

class PlaylistTrackAddRequest(BaseModel):
    trackId: str

class PlaylistResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    coverArtUrl: Optional[str] = None
    userId: str
    userName: str
    isPublic: bool
    trackCount: int = 0
    totalDurationSeconds: int = 0
    createdAt: datetime
    updatedAt: datetime
    tracks: Optional[List[TrackResponse]] = None

    model_config = ConfigDict(from_attributes=True)

# ------------------------------------------------------------------------------
# Search & Playback Schemas
# ------------------------------------------------------------------------------
class SearchResultResponse(BaseModel):
    tracks: List[TrackResponse] = []
    albums: List[AlbumResponse] = []
    artists: List[ArtistResponse] = []
    onlineTracks: List[dict] = []

class PlaybackSessionCreate(BaseModel):
    trackId: str
    deviceId: str = "web-client"

class PlaybackSessionResponse(BaseModel):
    sessionId: str
    userId: str
    deviceId: str
    trackId: str
    positionSeconds: float
    isPlaying: bool
    updatedAt: datetime

class PlaybackHeartbeatRequest(BaseModel):
    positionSeconds: float
    isPlaying: bool
