from jarvis.system.macos_control import open_url
from jarvis.utils.logging import get_logger

log = get_logger("tools.youtube_open")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "youtube_open",
        "description": "Search YouTube for a video and open the best matching result in the browser.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, e.g. the video title or topic.",
                }
            },
            "required": ["query"],
        },
    },
}


def run(args: dict) -> str:
    import yt_dlp

    query = args["query"]
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
    open_url(url)
    return f"Opened '{title}' on YouTube."
