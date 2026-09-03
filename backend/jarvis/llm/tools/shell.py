import subprocess

from jarvis.utils.logging import get_logger

log = get_logger("tools.shell")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_shell_command",
        "description": (
            "Run a bash command directly on this Mac and return its output "
            "(stdout+stderr, truncated). For anything destructive or critical — "
            "deleting/overwriting files, killing processes, shutdown/restart, sudo, "
            "formatting/erasing a disk — you MUST first tell the user exactly what "
            "command you're about to run and get an explicit yes in their next "
            "message before calling this tool. Safe read-only commands (listing "
            "files, checking status/processes) can run immediately without asking."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to run."}
            },
            "required": ["command"],
        },
    },
}


def run(args: dict) -> str:
    command = args["command"]
    log.info("running shell command: %s", command)
    try:
        result = subprocess.run(
            ["bash", "-lc", command], capture_output=True, text=True, timeout=30
        )
    except subprocess.TimeoutExpired:
        return "Komut 30 saniyede bitmedi, zaman aşımına uğradı."

    output = (result.stdout + result.stderr).strip()
    if not output:
        return f"(çıktı yok, exit code={result.returncode})"
    return output[:4000]
