from jarvis.system.macos_control import open_app as _open_app

SCHEMA = {
    "type": "function",
    "function": {
        "name": "open_app",
        "description": "Open a macOS application by name (e.g. 'Notes', 'Safari', 'Calendar').",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "The application's display name."}
            },
            "required": ["app_name"],
        },
    },
}


def run(args: dict) -> str:
    return _open_app(args["app_name"])
