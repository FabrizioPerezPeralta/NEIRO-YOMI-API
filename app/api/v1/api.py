from fastapi import APIRouter
from .endpoints import auth, tracks, albums, artists, playlists, favorites, search, playback

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tracks.router, prefix="/tracks", tags=["Tracks & Audio"])
api_router.include_router(albums.router, prefix="/albums", tags=["Albums"])
api_router.include_router(artists.router, prefix="/artists", tags=["Artists"])
api_router.include_router(playlists.router, prefix="/playlists", tags=["Playlists"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["Favorites"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(playback.router, prefix="/playback", tags=["Playback & Sessions"])

