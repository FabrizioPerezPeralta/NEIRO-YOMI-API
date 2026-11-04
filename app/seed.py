import os
import sys

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import wave
import math
import struct
from sqlalchemy.orm import Session
from .core.database import SessionLocal
from .core.config import settings
from .core.security import hash_password
from .models.models import User, Artist, Album, Track, AudioAsset, Playlist, PlaylistTrack
from .services.audio_extractor import AudioMetadataExtractor

def generate_sample_wav(
    filepath: str,
    duration_seconds: float = 8.0,
    sample_rate: int = 48000,
    channels: int = 2,
    base_freq: float = 432.0
):
    """
    Synthesizes a pleasant audiophile harmonic acoustic soundscape (432Hz root chord)
    using pure mathematical synthesis and standard library wave module.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    num_samples = int(duration_seconds * sample_rate)

    with wave.open(filepath, "w") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2) # 16-bit PCM
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Smooth envelope: fade-in and fade-out
            envelope = 1.0
            fade_len = 1.0
            if t < fade_len:
                envelope = t / fade_len
            elif t > duration_seconds - fade_len:
                envelope = (duration_seconds - t) / fade_len

            # Harmonic chord (Root, Major Third, Fifth, Octave, with slight stereo panning)
            f1 = base_freq
            f2 = base_freq * 1.25 # E
            f3 = base_freq * 1.50 # G
            f4 = base_freq * 2.00 # High Root

            sig_left = (
                0.35 * math.sin(2.0 * math.pi * f1 * t) +
                0.25 * math.sin(2.0 * math.pi * f2 * t) +
                0.20 * math.sin(2.0 * math.pi * f3 * t) +
                0.15 * math.sin(2.0 * math.pi * f4 * t)
            ) * envelope

            sig_right = (
                0.35 * math.sin(2.0 * math.pi * f1 * t + 0.1) +
                0.20 * math.sin(2.0 * math.pi * f2 * t - 0.1) +
                0.25 * math.sin(2.0 * math.pi * f3 * t + 0.1) +
                0.15 * math.sin(2.0 * math.pi * f4 * t)
            ) * envelope

            val_left = int(max(-32767, min(32767, sig_left * 28000)))
            val_right = int(max(-32767, min(32767, sig_right * 28000)))

            frames.extend(struct.pack("<hh", val_left, val_right))

        wav_file.writeframes(frames)

def seed_initial_data():
    db: Session = SessionLocal()
    try:
        # Check if already seeded
        existing_user = db.query(User).filter(User.username == "audiophile").first()
        if existing_user:
            return

        print("[Seed] Seeding initial audiophile database and sample audio files...")

        # 1. Create Default Demo User
        demo_user = User(
            email="audiophile@neiro-yomi.com",
            username="audiophile",
            display_name="Neiro Listener",
            hashed_password=hash_password("password123"),
            role="user"
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

        # 2. Create Artists
        artist1 = Artist(
            name="Kenjiro Wada (和田 健次郎)",
            biography="Contemporary Japanese ambient composer exploring spatial acoustics and microtonal textures.",
            genres="Ambient, Modern Classical, Minimalism",
            country="Japan",
            is_verified=True
        )
        artist2 = Artist(
            name="Aethelgard Trio",
            biography="Nordic chamber jazz ensemble dedicated to acoustic purity and analog mastering.",
            genres="Acoustic Jazz, Hi-Res Chamber",
            country="Norway",
            is_verified=True
        )
        db.add_all([artist1, artist2])
        db.commit()
        db.refresh(artist1)
        db.refresh(artist2)

        # 3. Create Albums
        album1 = Album(
            title="Kanazawa Rain (金沢の雨)",
            artist_id=artist1.id,
            release_date="2026-03-21",
            year=2026,
            genre="Ambient",
            total_tracks=2,
            total_duration_seconds=16,
            is_hires=True
        )
        album2 = Album(
            title="Nordic Timber & Stone",
            artist_id=artist2.id,
            release_date="2026-01-15",
            year=2026,
            genre="Acoustic Jazz",
            total_tracks=1,
            total_duration_seconds=8,
            is_hires=True
        )
        db.add_all([album1, album2])
        db.commit()
        db.refresh(album1)
        db.refresh(album2)

        # 4. Generate Audio Files on Disk
        track1_path = os.path.join(settings.AUDIO_DIR, "kanazawa_rain.wav")
        track2_path = os.path.join(settings.AUDIO_DIR, "enso_waves.wav")
        track3_path = os.path.join(settings.AUDIO_DIR, "nordic_whisper.wav")

        generate_sample_wav(track1_path, duration_seconds=10.0, sample_rate=96000, base_freq=432.0)
        generate_sample_wav(track2_path, duration_seconds=8.0, sample_rate=48000, base_freq=528.0)
        generate_sample_wav(track3_path, duration_seconds=8.0, sample_rate=96000, base_freq=396.0)

        meta1 = AudioMetadataExtractor.extract(track1_path)
        meta2 = AudioMetadataExtractor.extract(track2_path)
        meta3 = AudioMetadataExtractor.extract(track3_path)

        # 5. Create Track entities
        t1 = Track(
            title="Kanazawa Rain (金沢の雨)",
            artist_id=artist1.id,
            album_id=album1.id,
            duration_seconds=meta1["duration_seconds"],
            track_number=1,
            disc_number=1,
            genre="Ambient",
            year=2026,
            codec="wav",
            sample_rate=meta1["sample_rate"],
            bit_depth=meta1["bit_depth"],
            bitrate=meta1["bitrate"],
            is_lossless=True,
            is_hires=True,
            file_path=track1_path,
            checksum_sha256=meta1["checksum_sha256"],
            uploaded_by=demo_user.id
        )
        t2 = Track(
            title="Enso Waves (円相)",
            artist_id=artist1.id,
            album_id=album1.id,
            duration_seconds=meta2["duration_seconds"],
            track_number=2,
            disc_number=1,
            genre="Ambient",
            year=2026,
            codec="wav",
            sample_rate=meta2["sample_rate"],
            bit_depth=meta2["bit_depth"],
            bitrate=meta2["bitrate"],
            is_lossless=True,
            is_hires=True,
            file_path=track2_path,
            checksum_sha256=meta2["checksum_sha256"],
            uploaded_by=demo_user.id
        )
        t3 = Track(
            title="Nordic Timber & Stone",
            artist_id=artist2.id,
            album_id=album2.id,
            duration_seconds=meta3["duration_seconds"],
            track_number=1,
            disc_number=1,
            genre="Acoustic Jazz",
            year=2026,
            codec="wav",
            sample_rate=meta3["sample_rate"],
            bit_depth=meta3["bit_depth"],
            bitrate=meta3["bitrate"],
            is_lossless=True,
            is_hires=True,
            file_path=track3_path,
            checksum_sha256=meta3["checksum_sha256"],
            uploaded_by=demo_user.id
        )
        db.add_all([t1, t2, t3])
        db.commit()
        db.refresh(t1)
        db.refresh(t2)
        db.refresh(t3)

        # 6. Audio Assets
        for t, path in [(t1, track1_path), (t2, track2_path), (t3, track3_path)]:
            size = os.path.getsize(path)
            asset = AudioAsset(
                track_id=t.id,
                storage_key=path,
                file_size_bytes=size,
                mime_type="audio/wav",
                channels=2,
                is_original=True
            )
            db.add(asset)

        # 7. Create Playlist
        playlist = Playlist(
            title="Master Listening Selection (厳選音源)",
            description="Pure uncompressed acoustics, high dynamic range, and spatial depth.",
            user_id=demo_user.id,
            is_public=True
        )
        db.add(playlist)
        db.commit()
        db.refresh(playlist)

        pt1 = PlaylistTrack(playlist_id=playlist.id, track_id=t1.id, position=0)
        pt2 = PlaylistTrack(playlist_id=playlist.id, track_id=t2.id, position=1)
        pt3 = PlaylistTrack(playlist_id=playlist.id, track_id=t3.id, position=2)
        db.add_all([pt1, pt2, pt3])
        db.commit()

        print("[Seed] Seeding completed successfully!")
    finally:
        db.close()

