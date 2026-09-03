SCHEMA_START = {
    "type": "function",
    "function": {
        "name": "start_gesture_control",
        "description": (
            "Turn on camera-based hand-gesture control of the mouse/keyboard "
            "('el kontrolüne geç' / Iron Man mode). Fist = left click, index "
            "finger only = right click, thumb+index pinch = drag, two-finger "
            "swipe = scroll or switch tabs. Only call this when the user "
            "explicitly asks to switch to hand control."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

SCHEMA_STOP = {
    "type": "function",
    "function": {
        "name": "stop_gesture_control",
        "description": "Turn off camera-based hand-gesture control and release the camera.",
        "parameters": {"type": "object", "properties": {}},
    },
}


def run_start(args: dict) -> str:
    from jarvis.vision.gesture_control import controller

    return controller.start()


def run_stop(args: dict) -> str:
    from jarvis.vision.gesture_control import controller

    return controller.stop()
