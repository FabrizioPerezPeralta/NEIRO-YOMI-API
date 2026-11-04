import os
import uuid
import logging
from typing import Optional
import requests
from ..core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    @classmethod
    def _upload_to_supabase(cls, bucket: str, filename: str, content: bytes, content_type: str) -> Optional[str]:
        """
        Uploads a binary asset to Supabase Storage bucket via REST API.
        Returns the public URL if successful.
        """
        if not settings.SUPABASE_URL:
            return None

        key = settings.SUPABASE_SERVICE_ROLE_KEY
        if not key:
            return None

        base_url = settings.SUPABASE_URL.rstrip("/")
        upload_url = f"{base_url}/storage/v1/object/{bucket}/{filename}"
        headers = {
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        try:
            res = requests.post(upload_url, headers=headers, data=content, timeout=45)
            if res.status_code in (200, 201):
                public_url = f"{base_url}/storage/v1/object/public/{bucket}/{filename}"
                logger.info(f"Successfully uploaded to Supabase Storage: {public_url}")
                return public_url
            else:
                logger.warning(f"Supabase storage upload returned HTTP {res.status_code}: {res.text}")
        except Exception as err:
            logger.error(f"Error uploading to Supabase Storage: {err}")

        return None

    @classmethod
    def save_audio_file(cls, file_content: bytes, extension: str) -> str:
        """
        Saves audio file locally and optionally syncs to Supabase Storage.
        Returns the local absolute file path for streaming.
        """
        unique_name = f"{uuid.uuid4()}.{extension.lstrip('.')}"
        local_path = os.path.join(settings.AUDIO_DIR, unique_name)

        # 1. Save local copy for zero-latency local caching and streaming
        with open(local_path, "wb") as f:
            f.write(file_content)

        # 2. If Supabase is enabled, upload to Supabase Audio Bucket asynchronously / in background
        if settings.STORAGE_PROVIDER == "supabase" and settings.SUPABASE_URL:
            mime = "audio/flac" if extension.lower() in ("flac",) else "audio/mpeg"
            cls._upload_to_supabase(settings.SUPABASE_BUCKET_AUDIO, unique_name, file_content, mime)

        return local_path

    @classmethod
    def save_artwork_file(cls, artwork_bytes: bytes, extension: str = "jpg") -> str:
        """
        Saves cover art. If Supabase is configured, uploads to Supabase Storage
        and returns the CDN public URL. Otherwise saves locally.
        """
        unique_name = f"{uuid.uuid4()}.{extension.lstrip('.')}"
        local_path = os.path.join(settings.ARTWORK_DIR, unique_name)

        # Save local copy
        with open(local_path, "wb") as f:
            f.write(artwork_bytes)

        # Try Supabase Storage upload
        if settings.STORAGE_PROVIDER == "supabase" or settings.SUPABASE_URL:
            mime_type = f"image/{'jpeg' if extension.lower() in ('jpg', 'jpeg') else extension.lower()}"
            public_url = cls._upload_to_supabase(settings.SUPABASE_BUCKET_ARTWORK, unique_name, artwork_bytes, mime_type)
            if public_url:
                return public_url

        # Fallback to local endpoint
        return f"/api/v1/tracks/artwork/{unique_name}"

    @staticmethod
    def get_audio_path(file_path: str) -> Optional[str]:
        if not file_path:
            return None

        # 1. Direct path check (works for both absolute and relative paths)
        if os.path.exists(file_path):
            return os.path.abspath(file_path)

        # 2. Check inside audio directory by filename
        candidate_audio = os.path.join(settings.AUDIO_DIR, os.path.basename(file_path))
        if os.path.exists(candidate_audio):
            return os.path.abspath(candidate_audio)

        # 3. Check inside storage directory by filename
        candidate_storage = os.path.join(settings.STORAGE_DIR, os.path.basename(file_path))
        if os.path.exists(candidate_storage):
            return os.path.abspath(candidate_storage)

        return None
