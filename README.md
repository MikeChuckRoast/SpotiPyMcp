# SpotiPy MCP

An [MCP](https://modelcontextprotocol.io) server for searching Spotify and
managing your playlists from Claude (or any MCP client). Built on
[spotipy](https://spotipy.readthedocs.io/).

## Features

**Search**
- `search_tracks`, `search_artists`, `search_albums` (supports advanced filters
  like `artist:`, `year:`, `genre:`)
- `get_track_details`, `get_artist_top_tracks`

**Playlist management**
- `list_my_playlists`, `get_playlist_tracks`
- `add_tracks_to_playlist`, `remove_tracks_from_playlist`
- `create_playlist`, `delete_playlist` — delete a playlist you own
- `unfollow_playlist` — remove a playlist (typically one you don't own) from
  your library without deleting it
- `search_and_add` — find the top match for a query and add it in one step

## Setup

### 1. Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Register the redirect URI

In the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard),
open your app → **Settings** → **Redirect URIs**, and add:

```
http://127.0.0.1:8888/callback
```

(Must match `SPOTIFY_REDIRECT_URI` in `.env`.)

### 3. Authorize once

```powershell
python auth_setup.py
```

A browser window opens; log in and grant access. A refresh token is cached to
`.cache` so you never have to log in again (the server refreshes it silently).

### 4. Register with Claude Desktop / Claude Code

Add this to your MCP client config (for Claude Desktop, `claude_desktop_config.json`).
Use absolute paths:

```json
{
  "mcpServers": {
    "spotipy": {
      "command": "~\\SpotiPy\\.venv\\Scripts\\python.exe",
      "args": ["~\\SpotiPy\\server.py"]
    }
  }
}
```

For **Claude Code**:

```powershell
claude mcp add spotipy -- "~\SpotiPy\.venv\Scripts\python.exe" "~\SpotiPy\server.py"
```

Restart the client, and the SpotiPy MCP tools become available.

## Configuration (`.env`)

| Key | Purpose |
|-----|---------|
| `SPOTIFY_CLIENT_ID` | Your app's client id |
| `SPOTIFY_CLIENT_SECRET` | Your app's client secret |
| `SPOTIFY_REDIRECT_URI` | Must match the dashboard; default `http://127.0.0.1:8888/callback` |
| `SPOTIFY_SCOPE` | OAuth scopes granted at authorization; default (if unset) is `playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative user-read-private user-library-modify`. `user-read-private` is silently required by the playlist-creation endpoint even though Spotify doesn't document it; `user-library-modify` is required by `delete_playlist` (it calls the [Remove Library Items](https://developer.spotify.com/documentation/web-api/reference/remove-library-items) endpoint). |

## Security notes

- `.env` and `.cache` hold secrets and are git-ignored. Do not commit them.
- If your client secret was ever exposed, rotate it in the Spotify dashboard.

## Note on discovery endpoints

Spotify **deprecated** the Recommendations, Audio Features, Audio Analysis, and
Related Artists endpoints for newly-created apps (Nov 2024). SpotiPy MCP therefore
relies on search filters and `get_artist_top_tracks` for discovery rather than
those endpoints.
