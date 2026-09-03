import http.server
import os
import socket
import tempfile
import threading
from pathlib import Path

from jarvis.utils.logging import get_logger

log = get_logger("tools.phone_share")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_to_phone",
        "description": (
            "Share a file (photo/document) from this Mac to a phone on the same "
            "WiFi — works with any phone (Honor, other Android, iPhone), no app "
            "pairing needed. Starts a short-lived local web link the user opens in "
            "their phone's browser to download the file. Give them the exact URL "
            "to type or say you've opened it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path of the file on this Mac to share."}
            },
            "required": ["file_path"],
        },
    },
}

SERVE_MINUTES = 10


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def run(args: dict) -> str:
    src = Path(args["file_path"]).expanduser()
    if not src.is_file():
        return f"'{src}' bulunamadı."

    serve_dir = Path(tempfile.mkdtemp(prefix="jarvis_share_"))
    link_path = serve_dir / src.name
    try:
        os.symlink(src, link_path)
    except OSError:
        link_path.write_bytes(src.read_bytes())

    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=str(serve_dir), **kw
    )
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", 0), handler)
    port = httpd.server_address[1]

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    threading.Timer(SERVE_MINUTES * 60, httpd.shutdown).start()

    url = f"http://{_lan_ip()}:{port}/{src.name}"
    log.info("sharing %s at %s for %d minutes", src, url, SERVE_MINUTES)
    return (
        f"Telefonunla aynı WiFi'de bu adresi tarayıcıda aç: {url} "
        f"(link {SERVE_MINUTES} dakika açık kalacak)."
    )
