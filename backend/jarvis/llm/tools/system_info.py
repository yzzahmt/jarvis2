import datetime
import platform

SCHEMA_DATETIME = {
    "type": "function",
    "function": {
        "name": "get_current_datetime",
        "description": "Get the current local date and time.",
        "parameters": {"type": "object", "properties": {}},
    },
}

SCHEMA_SYSINFO = {
    "type": "function",
    "function": {
        "name": "get_system_info",
        "description": "Get basic info about the computer Jarvis is running on (OS, version, machine).",
        "parameters": {"type": "object", "properties": {}},
    },
}


def run_datetime(_args: dict) -> str:
    now = datetime.datetime.now().astimezone()
    return now.strftime("%A, %Y-%m-%d %H:%M:%S %Z")


def run_sysinfo(_args: dict) -> str:
    return f"{platform.system()} {platform.release()} on {platform.machine()}"
