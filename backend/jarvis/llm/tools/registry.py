from __future__ import annotations

from typing import Callable

from jarvis.llm.tools import (
    add_to_cart,
    compare_prices,
    gesture,
    open_app,
    open_dev_console,
    phone_share,
    shell,
    system_info,
    web_search,
    windows_transfer,
    youtube_open,
)

ToolFn = Callable[[dict], str]

TOOL_SCHEMAS: list[dict] = [
    open_app.SCHEMA,
    web_search.SCHEMA,
    youtube_open.SCHEMA,
    system_info.SCHEMA_DATETIME,
    system_info.SCHEMA_SYSINFO,
    compare_prices.SCHEMA,
    add_to_cart.SCHEMA,
    open_dev_console.SCHEMA,
    shell.SCHEMA,
    windows_transfer.SCHEMA,
    phone_share.SCHEMA,
    gesture.SCHEMA_START,
    gesture.SCHEMA_STOP,
]

TOOL_FUNCTIONS: dict[str, ToolFn] = {
    "open_app": open_app.run,
    "web_search": web_search.run,
    "youtube_open": youtube_open.run,
    "get_current_datetime": system_info.run_datetime,
    "get_system_info": system_info.run_sysinfo,
    "compare_prices": compare_prices.run,
    "add_to_cart": add_to_cart.run,
    "open_developer_console": open_dev_console.run,
    "run_shell_command": shell.run,
    "transfer_file_windows": windows_transfer.run,
    "send_to_phone": phone_share.run,
    "start_gesture_control": gesture.run_start,
    "stop_gesture_control": gesture.run_stop,
}
