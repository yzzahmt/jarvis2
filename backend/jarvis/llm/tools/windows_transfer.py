import subprocess

from jarvis.config import load_config
from jarvis.utils.logging import get_logger

log = get_logger("tools.windows_transfer")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "transfer_file_windows",
        "description": (
            "Copy a file between this Mac and the user's Windows PC over SSH/SCP. "
            "direction='to_windows' sends a local Mac file to the Windows PC; "
            "'from_windows' pulls a file from the Windows PC onto this Mac. "
            "Requires the Windows PC's host/user to already be set in Settings."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["to_windows", "from_windows"]},
                "local_path": {"type": "string", "description": "Path on this Mac."},
                "remote_path": {"type": "string", "description": "Path on the Windows PC."},
            },
            "required": ["direction", "local_path", "remote_path"],
        },
    },
}


def run(args: dict) -> str:
    cfg = load_config().devices
    if not cfg.windows_host or not cfg.windows_user:
        return (
            "Windows bilgisayarı henüz ayarlanmamış — Ayarlar'dan (ya da config'ten) "
            "windows_host ve windows_user değerlerini girmen gerekiyor. Ayrıca Windows "
            "tarafında OpenSSH Server açık olmalı (Ayarlar > Uygulamalar > İsteğe Bağlı "
            "Özellikler > OpenSSH Server)."
        )

    target = f"{cfg.windows_user}@{cfg.windows_host}"
    scp_cmd = ["scp"]
    if cfg.windows_ssh_key_path:
        scp_cmd += ["-i", cfg.windows_ssh_key_path]
    scp_cmd += ["-o", "ConnectTimeout=10"]

    local_path = args["local_path"]
    remote_path = args["remote_path"]
    if args["direction"] == "to_windows":
        scp_cmd += [local_path, f"{target}:{remote_path}"]
        dest_desc = f"Windows'ta {remote_path}"
    else:
        scp_cmd += [f"{target}:{remote_path}", local_path]
        dest_desc = f"Mac'te {local_path}"

    try:
        result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "Transfer 60 saniyede tamamlanmadı, bağlantıyı kontrol et."

    if result.returncode != 0:
        return f"Transfer başarısız: {result.stderr.strip()[:400]}"
    return f"Transfer tamamlandı — {dest_desc} konumuna kopyalandı."
