from jarvis.system.macos_control import open_url
from jarvis.utils.logging import get_logger

log = get_logger("tools.youtube_open")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "youtube_open",
        "description": (
            "Search YouTube for a video and open the best matching result in the "
            "browser. If the user asked to start at a specific point (e.g. '2. "
            "dakikasından aç'), pass timestamp_seconds so playback starts there."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, e.g. the video title or topic.",
                },
                "timestamp_seconds": {
                    "type": "integer",
                    "description": "Second to start playback at, if the user specified one.",
                },
            },
            "required": ["query"],
        },
    },
}


def run(args: dict) -> str:
    import yt_dlp

    query = args["query"]
    timestamp = args.get("timestamp_seconds")

    opts = {"quiet": True, "noplaylist": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)

    entries = info.get("entries") or []
    if not entries:
        return f"No YouTube results found for '{query}'."

    entry = entries[0]
    video_id = entry["id"]
    title = entry.get("title", query)
    url = f"https://www.youtube.com/watch?v={video_id}"
    if timestamp:
        url += f"&t={int(timestamp)}s"
    open_url(url)
    suffix = f" ({int(timestamp)}. saniyeden)" if timestamp else ""
    return f"Opened '{title}' on YouTube{suffix}."
