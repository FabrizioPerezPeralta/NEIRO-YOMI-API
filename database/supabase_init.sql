-- ==============================================================================
-- NEIRO YOMI • Supabase PostgreSQL Schema & Storage Provisioning
-- Executable in the Supabase SQL Editor (1-Click Setup)
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Trigram fuzzy matching for music search

-- -----------------------------------------------------------------------------
-- 2. Tables Schema
-- -----------------------------------------------------------------------------

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name VARCHAR(150),
    role VARCHAR(50) DEFAULT 'user',
    avatar_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Artists Table
CREATE TABLE IF NOT EXISTS artists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    biography TEXT,
    image_url VARCHAR(500),
    country VARCHAR(100),
    genres VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name);
CREATE INDEX IF NOT EXISTS idx_artists_name_trgm ON artists USING gin (name gin_trgm_ops);

-- Albums Table
CREATE TABLE IF NOT EXISTS albums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    artist_id UUID REFERENCES artists(id) ON DELETE CASCADE,
    cover_art_url VARCHAR(500),
    release_date VARCHAR(50),
    year INTEGER,
    genre VARCHAR(100),
    total_tracks INTEGER DEFAULT 0,
    total_duration_seconds INTEGER DEFAULT 0,
    is_hires BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_albums_title ON albums(title);
CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist_id);
CREATE INDEX IF NOT EXISTS idx_albums_title_trgm ON albums USING gin (title gin_trgm_ops);

-- Tracks Table (Technical Audiophile Metadata)
CREATE TABLE IF NOT EXISTS tracks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    artist_id UUID REFERENCES artists(id) ON DELETE CASCADE,
    album_id UUID REFERENCES albums(id) ON DELETE SET NULL,
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    track_number INTEGER,
    disc_number INTEGER DEFAULT 1,
    genre VARCHAR(100),
    year INTEGER,
    codec VARCHAR(50) NOT NULL,
    sample_rate INTEGER NOT NULL,
    bit_depth INTEGER,
    bitrate INTEGER,
    is_lossless BOOLEAN DEFAULT FALSE,
    is_hires BOOLEAN DEFAULT FALSE,
    file_path VARCHAR(500) NOT NULL,
    checksum_sha256 VARCHAR(64),
    cover_art_url VARCHAR(500),
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_id);
CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album_id);
CREATE INDEX IF NOT EXISTS idx_tracks_hires ON tracks(is_hires);
CREATE INDEX IF NOT EXISTS idx_tracks_title_trgm ON tracks USING gin (title gin_trgm_ops);

-- Audio Assets Table (Binary keys & storage mappings)
CREATE TABLE IF NOT EXISTS audio_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    storage_key VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    channels INTEGER DEFAULT 2,
    is_original BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Playlists Table
CREATE TABLE IF NOT EXISTS playlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    cover_art_url VARCHAR(500),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Playlist Tracks Table
CREATE TABLE IF NOT EXISTS playlist_tracks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    playlist_id UUID REFERENCES playlists(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    position INTEGER DEFAULT 0,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Favorites Table
CREATE TABLE IF NOT EXISTS favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_track ON favorites(track_id);

-- User Listening History Table
CREATE TABLE IF NOT EXISTS listening_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    listened_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completion_rate REAL DEFAULT 1.0,
    playback_context VARCHAR(100) DEFAULT 'web_player'
);

CREATE INDEX IF NOT EXISTS idx_history_user_date ON listening_history(user_id, listened_at DESC);

-- Devices Table (Active streaming clients)
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    device_name VARCHAR(255) NOT NULL,
    device_type VARCHAR(50) DEFAULT 'web',
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Playback Sessions Table (Real-time synchronization across devices)
CREATE TABLE IF NOT EXISTS playback_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(100) NOT NULL,
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    position_seconds REAL DEFAULT 0.0,
    is_playing BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Licenses Table
CREATE TABLE IF NOT EXISTS licenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id UUID REFERENCES tracks(id) ON DELETE CASCADE,
    license_type VARCHAR(100) DEFAULT 'personal_locker',
    rights_holder VARCHAR(255),
    territory VARCHAR(100) DEFAULT 'worldwide',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Preferences Table
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    preferred_quality VARCHAR(50) DEFAULT 'lossless',
    equalizer_preset VARCHAR(50) DEFAULT 'flat',
    dark_mode BOOLEAN DEFAULT TRUE,
    crossfade_seconds REAL DEFAULT 0.0
);

-- Uploads Table (Tracking processing pipeline)
CREATE TABLE IF NOT EXISTS uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 3. Supabase Storage Buckets Provisioning
-- -----------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public)
VALUES ('neiro-artwork', 'neiro-artwork', true)
ON CONFLICT (id) DO NOTHING;

INSERT INTO storage.buckets (id, name, public)
VALUES ('neiro-audio', 'neiro-audio', true)
ON CONFLICT (id) DO NOTHING;

-- Storage Public Read Access Policies
CREATE POLICY "Public Artwork Access" ON storage.objects
    FOR SELECT USING (bucket_id = 'neiro-artwork');

CREATE POLICY "Public Audio Stream Access" ON storage.objects
    FOR SELECT USING (bucket_id = 'neiro-audio');

-- -----------------------------------------------------------------------------
-- 4. Initial Seed Data (Demo Audiophile Member & Master Recordings)
-- -----------------------------------------------------------------------------
-- Demo user: audiophile / password123 (bcrypt hash: $2b$12$609t2uL2iJ6N7e0rB8sJYe3bHwK9Z9HkQz.1l1XGZ5B4Y6bV.8b.m)
INSERT INTO users (id, email, username, hashed_password, display_name, role)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'audiophile@neiro.internal',
    'audiophile',
    '$2b$12$LhWk20B6rZqG83N.lSJE6eT99.g81oQYqfCcvYc1vV3a6a9/X5u/y',
    'Neiro Listener',
    'audiophile_member'
) ON CONFLICT (email) DO NOTHING;

-- Demo Artist
INSERT INTO artists (id, name, biography, country, genres, is_verified)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'Noriko Matsueda & Takahito Eguchi',
    'Renowned Japanese composers specializing in acoustic piano, spatial resonance, and orchestral master recordings.',
    'Japan',
    'Classical, Acoustic, Ambient, Game Master',
    true
) ON CONFLICT DO NOTHING;

-- Demo Album
INSERT INTO albums (id, title, artist_id, release_date, year, genre, total_tracks, is_hires)
VALUES (
    'c0000000-0000-0000-0000-000000000001',
    'Hokuriku Ambient Sessions',
    'b0000000-0000-0000-0000-000000000001',
    '2024-03-15',
    2024,
    'Acoustic / Ambient',
    1,
    true
) ON CONFLICT DO NOTHING;

-- Demo Master Track: Kanazawa Rain
INSERT INTO tracks (
    id, title, artist_id, album_id, duration_seconds, track_number, genre, year,
    codec, sample_rate, bit_depth, bitrate, is_lossless, is_hires, file_path, checksum_sha256
) VALUES (
    'd0000000-0000-0000-0000-000000000001',
    'Kanazawa Rain (金沢の雨)',
    'b0000000-0000-0000-0000-000000000001',
    'c0000000-0000-0000-0000-000000000001',
    342.5,
    1,
    'Acoustic',
    2024,
    'flac',
    96000,
    24,
    4608,
    true,
    true,
    'audio/kanazawa_rain_master.flac',
    'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0'
) ON CONFLICT DO NOTHING;

