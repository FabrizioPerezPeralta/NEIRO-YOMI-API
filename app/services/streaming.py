import os
import mimetypes
from typing import Generator, Optional
from fastapi import Request, HTTPException, status
from starlette.responses import StreamingResponse

CHUNK_SIZE = 128 * 1024  # 128 KB for smooth high-fidelity buffering

def get_audio_mime_type(file_path: str, codec: str) -> str:
    ext_map = {
        "flac": "audio/flac",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "aac": "audio/aac",
        "opus": "audio/opus",
        "alac": "audio/m4a",
        "aiff": "audio/aiff"
    }
    if codec.lower() in ext_map:
        return ext_map[codec.lower()]
    guessed, _ = mimetypes.guess_type(file_path)
    return guessed or "audio/octet-stream"

def stream_audio_file(
    file_path: str,
    codec: str,
    request: Request
) -> StreamingResponse:
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found on disk")

    file_size = os.path.getsize(file_path)
    mime_type = get_audio_mime_type(file_path, codec)

    range_header = request.headers.get("range")
    if not range_header:
        # Full content stream (HTTP 200)
        def iterfile() -> Generator[bytes, None, None]:
            with open(file_path, mode="rb") as file_like:
                while chunk := file_like.read(CHUNK_SIZE):
                    yield chunk

        headers = {
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Type": mime_type,
            "Cache-Control": "public, max-age=31536000, immutable",
        }
        return StreamingResponse(iterfile(), headers=headers, media_type=mime_type)

    # Range request stream (HTTP 206 Partial Content)
    try:
        range_value = range_header.replace("bytes=", "").strip()
        parts = range_value.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
    except ValueError:
        raise HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, detail="Invalid Range header")

    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"},
            detail="Range out of bounds"
        )

    content_length = (end - start) + 1

    def iter_range() -> Generator[bytes, None, None]:
        with open(file_path, mode="rb") as f:
            f.seek(start)
            bytes_left = content_length
            while bytes_left > 0:
                read_size = min(CHUNK_SIZE, bytes_left)
                data = f.read(read_size)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
        "Cache-Control": "no-cache",
    }

    return StreamingResponse(
        iter_range(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
        media_type=mime_type,
    )

