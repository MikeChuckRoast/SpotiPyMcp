"""Spotify authentication and a thin, MCP-friendly wrapper around spotipy.

Auth uses the Authorization Code flow so we can both read *and* modify the
signed-in user's playlists. The refresh token is cached to `.cache` after a
one-time browser login (run `python auth_setup.py` once).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# Load .env from this file's directory, regardless of the process CWD (important
# when Claude Desktop launches the server from an arbitrary working directory).
_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")

_CACHE_PATH = _BASE_DIR / ".cache"


def _auth_manager(open_browser: bool) -> SpotifyOAuth:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    scope = os.getenv("SPOTIFY_SCOPE", "playlist-modify-public playlist-modify-private "
                                       "playlist-read-private playlist-read-collaborative "
                                       "user-read-private user-library-modify")

    if not client_id or not client_secret:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET missing. "
            f"Check {_BASE_DIR / '.env'}."
        )

    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=str(_CACHE_PATH),
        open_browser=open_browser,
    )


@lru_cache(maxsize=1)
def get_client(open_browser: bool = False) -> spotipy.Spotify:
    """Return a cached, authenticated Spotify client.

    When run under an MCP client (stdio), `open_browser` stays False so nothing
    is written to stdout; it relies on the `.cache` token from `auth_setup.py`.
    """
    if not _CACHE_PATH.exists() and not open_browser:
        raise RuntimeError(
            "No cached Spotify credentials found. Run `python auth_setup.py` "
            "once to authorize this app in your browser."
        )
    return spotipy.Spotify(auth_manager=_auth_manager(open_browser=open_browser))


# --- Formatting helpers: turn verbose API payloads into compact, LLM-friendly dicts ---

def format_track(item: dict) -> dict:
    """Flatten a track object to the fields that matter."""
    if item is None:
        return {}
    artists = ", ".join(a["name"] for a in item.get("artists", []))
    album = item.get("album", {}) or {}
    external_ids = item.get("external_ids", {}) or {}
    return {
        "name": item.get("name"),
        "artists": artists,
        "album": album.get("name"),
        "album_release_date": album.get("release_date"),
        "album_images": album.get("images"),
        "uri": item.get("uri"),
        "id": item.get("id"),
        "duration_ms": item.get("duration_ms"),
        "explicit": item.get("explicit"),
        "track_number": item.get("track_number"),
        "disc_number": item.get("disc_number"),
        "isrc": external_ids.get("isrc"),
        "url": (item.get("external_urls") or {}).get("spotify"),
    }


def format_playlist(item: dict) -> dict:
    if item is None:
        return {}
    return {
        "name": item.get("name"),
        "id": item.get("id"),
        "owner": (item.get("owner") or {}).get("display_name"),
        "description": item.get("description"),
        "public": item.get("public"),
        "collaborative": item.get("collaborative"),
        "track_count": (item.get("tracks") or {}).get("total"),
        "followers": (item.get("followers") or {}).get("total"),
        "images": item.get("images"),
        "url": (item.get("external_urls") or {}).get("spotify"),
    }


def format_artist(item: dict) -> dict:
    if item is None:
        return {}
    return {
        "name": item.get("name"),
        "id": item.get("id"),
        "uri": item.get("uri"),
        "genres": item.get("genres", []),
        "followers": (item.get("followers") or {}).get("total"),
        "url": (item.get("external_urls") or {}).get("spotify"),
    }
