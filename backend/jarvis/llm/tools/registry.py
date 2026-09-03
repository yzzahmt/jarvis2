from __future__ import annotations

from typing import Callable

from jarvis.llm.tools import open_app, system_info, web_search, youtube_open

ToolFn = Callable[[dict], str]

TOOL_SCHEMAS: list[dict] = [
    open_app.SCHEMA,
    web_search.SCHEMA,
    youtube_open.SCHEMA,
    system_info.SCHEMA_DATETIME,
    system_info.SCHEMA_SYSINFO,
]

TOOL_FUNCTIONS: dict[str, ToolFn] = {
    "open_app": open_app.run,
    "web_search": web_search.run,
    "youtube_open": youtube_open.run,
    "get_current_datetime": system_info.run_datetime,
    "get_system_info": system_info.run_sysinfo,
}
