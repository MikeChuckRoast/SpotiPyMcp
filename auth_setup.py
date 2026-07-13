"""One-time interactive authorization.

Run this once (`python auth_setup.py`) before using the MCP server. It opens a
browser so you can grant the app access to your playlists, then caches a refresh
token to `.cache`. After that the MCP server authenticates silently.
"""

from spotify_client import get_client


def main() -> None:
    print("Opening your browser to authorize SpotiPy MCP with Spotify...")
    # open_browser=True triggers the interactive OAuth flow if no cache exists.
    sp = get_client.__wrapped__(open_browser=True)  # bypass lru_cache
    me = sp.current_user()
    print(f"\n✅ Authorized as {me.get('display_name')} (id: {me.get('id')}).")
    print("Token cached to .cache — you can now run the MCP server.")


if __name__ == "__main__":
    main()
