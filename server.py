"""SpotiPy MCP — an MCP server for searching Spotify and managing your playlists.

Run standalone for a quick check: `python server.py`
Or register it with Claude Desktop / Claude Code (see README.md).
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from spotify_client import (
    format_artist,
    format_playlist,
    format_track,
    get_client,
)

mcp = FastMCP("SpotiPyMcp")


# ----------------------------------------------------------------------------
# Search & discovery
# ----------------------------------------------------------------------------

@mcp.tool()
def search_tracks(query: str, limit: int = 10) -> list[dict]:
    """Search Spotify for tracks.

    Supports advanced field filters in the query, e.g.
    'artist:radiohead track:creep', 'year:2020-2023', 'genre:jazz'.
    Returns a list of tracks with their URIs (needed to add them to playlists).
    """
    sp = get_client()
    results = sp.search(q=query, type="track", limit=min(limit, 50))
    items = (results.get("tracks") or {}).get("items", [])
    return [format_track(t) for t in items]


@mcp.tool()
def search_artists(query: str, limit: int = 10) -> list[dict]:
    """Search Spotify for artists by name."""
    sp = get_client()
    results = sp.search(q=query, type="artist", limit=min(limit, 50))
    items = (results.get("artists") or {}).get("items", [])
    return [format_artist(a) for a in items]


@mcp.tool()
def search_albums(query: str, limit: int = 10) -> list[dict]:
    """Search Spotify for albums. Returns name, artists, id and uri."""
    sp = get_client()
    results = sp.search(q=query, type="album", limit=min(limit, 50))
    items = (results.get("albums") or {}).get("items", [])
    return [
        {
            "name": a.get("name"),
            "artists": ", ".join(ar["name"] for ar in a.get("artists", [])),
            "id": a.get("id"),
            "uri": a.get("uri"),
            "release_date": a.get("release_date"),
            "total_tracks": a.get("total_tracks"),
        }
        for a in items
    ]


@mcp.tool()
def get_track_details(track_id: str) -> dict:
    """Get full details for a single track by its Spotify id or URI."""
    sp = get_client()
    return format_track(sp.track(track_id))


@mcp.tool()
def get_artist_top_tracks(artist_id: str, country: str = "US") -> list[dict]:
    """Get an artist's most popular tracks (useful for discovery)."""
    sp = get_client()
    results = sp.artist_top_tracks(artist_id, country=country)
    return [format_track(t) for t in results.get("tracks", [])]


# ----------------------------------------------------------------------------
# Playlist management
# ----------------------------------------------------------------------------

@mcp.tool()
def list_my_playlists(limit: int = 50) -> list[dict]:
    """List the playlists owned or followed by the signed-in user."""
    sp = get_client()
    results = sp.current_user_playlists(limit=min(limit, 50))
    return [format_playlist(p) for p in results.get("items", [])]


@mcp.tool()
def get_playlist_tracks(playlist_id: str, limit: int = 500) -> list[dict]:
    """List the tracks in a playlist.

    Pages through the playlist so playlists longer than one API page (100) are
    fully returned, up to `limit` tracks.
    """
    sp = get_client()
    tracks: list[dict] = []
    results = sp.playlist_items(playlist_id, limit=100)
    while results:
        for entry in results.get("items", []):
            # Spotify returns the playlist entry under "track" (or "item" for the
            # newer unified track/episode shape); support both.
            track = entry.get("track") or entry.get("item")
            if track and track.get("uri"):  # skip removed/unavailable entries
                tracks.append(format_track(track))
                if len(tracks) >= limit:
                    return tracks
        results = sp.next(results) if results.get("next") else None
    return tracks


@mcp.tool()
def add_tracks_to_playlist(playlist_id: str, track_uris: list[str]) -> dict:
    """Add one or more tracks to a playlist.

    `track_uris` are Spotify track URIs (e.g. 'spotify:track:...') as returned
    by the search tools.
    """
    sp = get_client()
    if not track_uris:
        return {"added": 0, "message": "No track URIs provided."}
    sp.playlist_add_items(playlist_id, track_uris)
    return {"added": len(track_uris), "playlist_id": playlist_id}


@mcp.tool()
def remove_tracks_from_playlist(playlist_id: str, track_uris: list[str]) -> dict:
    """Remove all occurrences of the given tracks from a playlist."""
    sp = get_client()
    if not track_uris:
        return {"removed": 0, "message": "No track URIs provided."}
    sp.playlist_remove_all_occurrences_of_items(playlist_id, track_uris)
    return {"removed": len(track_uris), "playlist_id": playlist_id}


@mcp.tool()
def create_playlist(
    name: str,
    description: str = "",
    public: bool = False,
) -> dict:
    """Create a new playlist owned by the signed-in user."""
    sp = get_client()
    playlist = sp.current_user_playlist_create(
        name=name,
        public=public,
        description=description,
    )
    return format_playlist(playlist)


@mcp.tool()
def unfollow_playlist(playlist_id: str) -> dict:
    """Unfollow a playlist (removes it from your library without deleting it).

    For playlists you don't own, this is how you "remove" them from your
    account — the playlist itself keeps existing for its owner and anyone
    else following it. For playlists you *own*, prefer `delete_playlist`.
    """
    sp = get_client()
    sp.current_user_unfollow_playlist(playlist_id)
    return {"unfollowed": True, "playlist_id": playlist_id}


@mcp.tool()
def delete_playlist(playlist_id: str) -> dict:
    """Delete a playlist you own by removing it from your library.

    Uses Spotify's "Remove Library Items" endpoint (DELETE /me/library),
    which spotipy doesn't wrap, so this calls it directly. Requires the
    `user-library-modify` scope.
    """
    sp = get_client()
    playlist_uri = f"spotify:playlist:{sp._get_id('playlist', playlist_id)}"
    sp._delete("me/library", uris=playlist_uri)
    return {"deleted": True, "playlist_id": playlist_id}


@mcp.tool()
def search_and_add(query: str, playlist_id: str) -> dict:
    """Convenience: find the top-matching track for a query and add it.

    Returns the matched track so you can confirm it grabbed the right song.
    """
    sp = get_client()
    results = sp.search(q=query, type="track", limit=1)
    items = (results.get("tracks") or {}).get("items", [])
    if not items:
        return {"added": False, "message": f"No track found for '{query}'."}
    track = format_track(items[0])
    sp.playlist_add_items(playlist_id, [track["uri"]])
    return {"added": True, "track": track, "playlist_id": playlist_id}


if __name__ == "__main__":
    # Default transport is stdio, which is what Claude Desktop/Code expect.
    mcp.run()
