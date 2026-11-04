import os
import struct
import hashlib
from typing import Dict, Any, Optional, Tuple

class AudioMetadataExtractor:
    """
    Audiophile audio metadata extractor.
    Parses native binary headers for FLAC, WAV, and MP3 files.
    Calculates technical audio specs and SHA-256 file integrity checksums.
    """

    @classmethod
    def extract(cls, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            header = f.read(12)

        file_size = os.path.getsize(file_path)
        sha256 = cls.compute_sha256(file_path)

        result: Dict[str, Any] = {
            "title": os.path.splitext(os.path.basename(file_path))[0],
            "artist": "Unknown Artist",
            "album": "Unknown Album",
            "genre": "Audiophile",
            "year": None,
            "track_number": 1,
            "disc_number": 1,
            "duration_seconds": 180.0,
            "codec": "wav",
            "sample_rate": 44100,
            "bit_depth": 16,
            "bitrate": 1411,
            "channels": 2,
            "is_lossless": True,
            "is_hires": False,
            "checksum_sha256": sha256,
            "file_size_bytes": file_size,
            "embedded_artwork": None, # bytes if extracted
        }

        # Check format
        if header.startswith(b"fLaC"):
            cls._parse_flac(file_path, result)
        elif header.startswith(b"RIFF") and header[8:12] == b"WAVE":
            cls._parse_wav(file_path, result)
        elif header.startswith(b"ID3") or header[:2] == b"\xff\xfb" or header[:2] == b"\xff\xf3":
            cls._parse_mp3(file_path, result)
        else:
            # Fallback by extension
            ext = os.path.splitext(file_path)[1].lower().replace(".", "")
            if ext in ["flac", "wav", "mp3", "aac", "opus", "alac"]:
                result["codec"] = ext

        # Calculate lossless and hi-res audio flags
        lossless_codecs = ["flac", "alac", "wav", "aiff"]
        result["is_lossless"] = result["codec"].lower() in lossless_codecs
        result["is_hires"] = (
            result["is_lossless"]
            and (result["sample_rate"] > 48000 or (result["bit_depth"] and result["bit_depth"] > 16))
        )

        return result

    @classmethod
    def compute_sha256(cls, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def _parse_flac(cls, file_path: str, result: Dict[str, Any]) -> None:
        result["codec"] = "flac"
        result["is_lossless"] = True

        with open(file_path, "rb") as f:
            magic = f.read(4)
            if magic != b"fLaC":
                return

            while True:
                header = f.read(4)
                if len(header) < 4:
                    break

                is_last = (header[0] & 0x80) != 0
                block_type = header[0] & 0x7F
                block_length = int.from_bytes(header[1:4], "big")
                block_data = f.read(block_length)

                if block_type == 0:  # STREAMINFO
                    if len(block_data) >= 34:
                        # Bits 80 to 99: Sample rate (20 bits)
                        # Bits 100 to 102: Channels - 1 (3 bits)
                        # Bits 103 to 107: Bits per sample - 1 (5 bits)
                        # Bits 108 to 143: Total samples (36 bits)
                        b10 = block_data[10]
                        b11 = block_data[11]
                        b12 = block_data[12]
                        b13 = block_data[13]

                        sample_rate = (b10 << 12) | (b11 << 4) | (b12 >> 4)
                        channels = ((b12 >> 1) & 0x07) + 1
                        bit_depth = (((b12 & 0x01) << 4) | (b13 >> 4)) + 1
                        total_samples = int.from_bytes(block_data[13:18], "big") & 0x0FFFFFFFFF

                        result["sample_rate"] = sample_rate
                        result["channels"] = channels
                        result["bit_depth"] = bit_depth
                        if sample_rate > 0:
                            duration = total_samples / sample_rate
                            result["duration_seconds"] = round(duration, 2)
                            if duration > 0:
                                result["bitrate"] = int((result["file_size_bytes"] * 8) / (duration * 1000))

                elif block_type == 4:  # VORBIS_COMMENT
                    cls._parse_vorbis_comment(block_data, result)

                elif block_type == 6:  # PICTURE
                    cls._parse_flac_picture(block_data, result)

                if is_last:
                    break

    @classmethod
    def _parse_vorbis_comment(cls, data: bytes, result: Dict[str, Any]) -> None:
        try:
            vendor_len = int.from_bytes(data[0:4], "little")
            offset = 4 + vendor_len
            user_comment_count = int.from_bytes(data[offset:offset+4], "little")
            offset += 4

            for _ in range(user_comment_count):
                if offset + 4 > len(data):
                    break
                comment_len = int.from_bytes(data[offset:offset+4], "little")
                offset += 4
                comment_bytes = data[offset:offset+comment_len]
                offset += comment_len
                comment_str = comment_bytes.decode("utf-8", errors="replace")

                if "=" in comment_str:
                    key, val = comment_str.split("=", 1)
                    key = key.upper().strip()
                    val = val.strip()

                    if key == "TITLE":
                        result["title"] = val
                    elif key in ["ARTIST", "PERFORMER"]:
                        result["artist"] = val
                    elif key == "ALBUM":
                        result["album"] = val
                    elif key == "GENRE":
                        result["genre"] = val
                    elif key in ["DATE", "YEAR"]:
                        try:
                            result["year"] = int(val[:4])
                        except Exception:
                            pass
                    elif key == "TRACKNUMBER":
                        try:
                            result["track_number"] = int(val.split("/")[0])
                        except Exception:
                            pass
        except Exception:
            pass

    @classmethod
    def _parse_flac_picture(cls, data: bytes, result: Dict[str, Any]) -> None:
        try:
            # Picture structure: type (4B), mime_len (4B), mime (str), desc_len (4B), desc (str),
            # width (4B), height (4B), depth (4B), colors (4B), data_len (4B), data
            offset = 4
            mime_len = int.from_bytes(data[offset:offset+4], "big")
            offset += 4 + mime_len
            desc_len = int.from_bytes(data[offset:offset+4], "big")
            offset += 4 + desc_len + 16 # Skip width, height, depth, colors
            data_len = int.from_bytes(data[offset:offset+4], "big")
            offset += 4
            if offset + data_len <= len(data):
                result["embedded_artwork"] = data[offset:offset+data_len]
        except Exception:
            pass

    @classmethod
    def _parse_wav(cls, file_path: str, result: Dict[str, Any]) -> None:
        result["codec"] = "wav"
        result["is_lossless"] = True

        with open(file_path, "rb") as f:
            riff_header = f.read(12)
            if len(riff_header) < 12 or riff_header[:4] != b"RIFF" or riff_header[8:12] != b"WAVE":
                return

            while True:
                chunk_header = f.read(8)
                if len(chunk_header) < 8:
                    break
                chunk_id = chunk_header[:4]
                chunk_size = int.from_bytes(chunk_header[4:8], "little")

                if chunk_id == b"fmt ":
                    fmt_data = f.read(chunk_size)
                    if len(fmt_data) >= 16:
                        # audio_format = int.from_bytes(fmt_data[0:2], "little")
                        channels = int.from_bytes(fmt_data[2:4], "little")
                        sample_rate = int.from_bytes(fmt_data[4:8], "little")
                        byte_rate = int.from_bytes(fmt_data[8:12], "little")
                        bits_per_sample = int.from_bytes(fmt_data[14:16], "little")

                        result["channels"] = channels
                        result["sample_rate"] = sample_rate
                        result["bit_depth"] = bits_per_sample
                        result["bitrate"] = int((byte_rate * 8) / 1000)

                elif chunk_id == b"data":
                    # Data chunk size gives duration
                    if result.get("bitrate", 0) > 0:
                        duration = (chunk_size * 8) / (result["bitrate"] * 1000)
                        result["duration_seconds"] = round(duration, 2)
                    f.seek(chunk_size, 1)
                else:
                    f.seek(chunk_size, 1)

    @classmethod
    def _parse_mp3(cls, file_path: str, result: Dict[str, Any]) -> None:
        result["codec"] = "mp3"
        result["is_lossless"] = False
        result["bit_depth"] = 16

        with open(file_path, "rb") as f:
            id3 = f.read(10)
            if id3.startswith(b"ID3"):
                # ID3v2 tag
                tag_size = ((id3[6] & 0x7F) << 21) | ((id3[7] & 0x7F) << 14) | ((id3[8] & 0x7F) << 7) | (id3[9] & 0x7F)
                tag_data = f.read(tag_size)
                cls._parse_id3v2(tag_data, result)

        # Estimate duration from file size and typical 320kbps MP3
        if result.get("bitrate") is None:
            result["bitrate"] = 320
        duration = (result["file_size_bytes"] * 8) / (result["bitrate"] * 1000)
        result["duration_seconds"] = round(duration, 2)

    @classmethod
    def _parse_id3v2(cls, data: bytes, result: Dict[str, Any]) -> None:
        offset = 0
        while offset + 10 < len(data):
            frame_id = data[offset:offset+4].decode("latin-1", errors="ignore")
            frame_size = int.from_bytes(data[offset+4:offset+8], "big")
            offset += 10
            if frame_size <= 0 or offset + frame_size > len(data):
                break

            frame_data = data[offset:offset+frame_size]
            offset += frame_size

            # Handle text frames
            if frame_id in ["TIT2", "TPE1", "TALB", "TCON", "TYER", "TDRC", "TRCK"]:
                try:
                    encoding = frame_data[0]
                    text_bytes = frame_data[1:]
                    if encoding == 0:
                        text = text_bytes.decode("latin-1").rstrip("\x00")
                    elif encoding == 1:
                        text = text_bytes.decode("utf-16").rstrip("\x00")
                    elif encoding == 3:
                        text = text_bytes.decode("utf-8").rstrip("\x00")
                    else:
                        text = text_bytes.decode("utf-8", errors="ignore").rstrip("\x00")

                    if frame_id == "TIT2":
                        result["title"] = text
                    elif frame_id == "TPE1":
                        result["artist"] = text
                    elif frame_id == "TALB":
                        result["album"] = text
                    elif frame_id == "TCON":
                        result["genre"] = text
                    elif frame_id in ["TYER", "TDRC"]:
                        try:
                            result["year"] = int(text[:4])
                        except Exception:
                            pass
                    elif frame_id == "TRCK":
                        try:
                            result["track_number"] = int(text.split("/")[0])
                        except Exception:
                            pass
                except Exception:
                    pass

            # Handle APIC (Attached picture)
            elif frame_id == "APIC":
                try:
                    # APIC: encoding (1B), mime_type (null-terminated), pic_type (1B), desc (null-terminated), pic_data
                    sub_offset = 1
                    mime_end = frame_data.find(b"\x00", sub_offset)
                    if mime_end != -1:
                        # Skip pic_type (1B)
                        sub_offset = mime_end + 2
                        desc_end = frame_data.find(b"\x00", sub_offset)
                        if desc_end != -1:
                            sub_offset = desc_end + 1
                            result["embedded_artwork"] = frame_data[sub_offset:]
                except Exception:
                    pass

