import os
import pytest
from api.app.core.database import SessionLocal
from api.app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from api.app.models.models import User, Track, Album, Artist, Playlist, PlaylistTrack, Favorite
from api.app.services.audio_extractor import AudioMetadataExtractor
from api.app.api.v1.endpoints.auth import register, login
from api.app.api.v1.endpoints.tracks import get_tracks, get_track
from api.app.api.v1.endpoints.albums import get_albums, get_album
from api.app.api.v1.endpoints.artists import get_artists, get_artist
from api.app.api.v1.endpoints.playlists import create_playlist, get_playlists, add_track_to_playlist
from api.app.api.v1.endpoints.favorites import toggle_favorite, get_favorites
from api.app.api.v1.endpoints.search import search
from api.app.schemas.schemas import RegisterRequest, LoginRequest, PlaylistCreate, PlaylistTrackAddRequest

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_password_hashing_and_jwt():
    pwd = "audiophile_test_password"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False

    token = create_access_token(subject="user_12345")
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_12345"

def test_seeded_data_integrity(db):
    tracks = db.query(Track).all()
    assert len(tracks) >= 3

    for t in tracks:
        assert t.title is not None
        assert t.codec in ["wav", "flac", "mp3"]
        assert t.sample_rate >= 44100
        assert t.checksum_sha256 is not None
        assert os.path.exists(t.file_path)

def test_audio_metadata_extractor(db):
    track = db.query(Track).first()
    meta = AudioMetadataExtractor.extract(track.file_path)
    assert meta["codec"] == "wav"
    assert meta["is_lossless"] is True
    assert meta["sample_rate"] == track.sample_rate
    assert meta["checksum_sha256"] == track.checksum_sha256

def test_auth_login(db):
    req = LoginRequest(username_or_email="audiophile", password="password123")
    res = login(req, db=db)
    assert res.user.username == "audiophile"
    assert res.accessToken is not None

def test_get_tracks_endpoint(db):
    tracks = get_tracks(db=db, current_user=None)
    assert len(tracks) >= 3
    first_track = tracks[0]
    assert first_track.id is not None
    assert first_track.streamUrl.startswith("/api/v1/tracks/")

def test_get_albums_and_artists(db):
    albums = get_albums(db=db)
    assert len(albums) >= 2
    artists = get_artists(db=db)
    assert len(artists) >= 2

def test_playlist_workflow(db):
    user = db.query(User).filter(User.username == "audiophile").first()
    track = db.query(Track).first()

    # Create Playlist
    pl_create = PlaylistCreate(title="Test Audiophile Session", description="Testing playlist features", isPublic=True)
    created = create_playlist(pl_create, db=db, current_user=user)
    assert created.title == "Test Audiophile Session"

    # Add track
    add_req = PlaylistTrackAddRequest(trackId=track.id)
    add_res = add_track_to_playlist(created.id, add_req, db=db, current_user=user)
    assert add_res["success"] is True

def test_favorite_toggle(db):
    user = db.query(User).filter(User.username == "audiophile").first()
    track = db.query(Track).first()

    # Reset state to clean baseline
    existing = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.track_id == track.id).first()
    if existing:
        db.delete(existing)
        db.commit()

    # Toggle favorite on
    res1 = toggle_favorite(track.id, db=db, current_user=user)
    assert res1["isFavorite"] is True

    # Check favorites list
    favs = get_favorites(db=db, current_user=user)
    assert any(f.id == track.id for f in favs)

    # Toggle favorite off
    res2 = toggle_favorite(track.id, db=db, current_user=user)
    assert res2["isFavorite"] is False

def test_search_endpoint(db):
    res = search(q="Kanazawa", db=db, current_user=None)
    assert len(res.tracks) >= 1
    assert "Kanazawa" in res.tracks[0].title

def test_import_local_directory(db):
    from api.app.api.v1.endpoints.tracks import import_local_directory
    res = import_local_directory(directory_path="./storage/audio", db=db, current_user=None)
    assert res["success"] is True
    assert "message" in res

def test_online_categories():
    from api.app.api.v1.endpoints.tracks import online_category, online_trending
    # Should safely return lists without crashing even in sandboxed environments
    cat_res = online_category("city_pop", limit=5)
    assert isinstance(cat_res, list)
    trend_res = online_trending(limit=5)
    assert isinstance(trend_res, list)
