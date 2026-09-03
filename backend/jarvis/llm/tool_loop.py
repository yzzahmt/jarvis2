from __future__ import annotations

from jarvis.llm.client import ChatResponse, LLMClient
from jarvis.llm.tools.registry import TOOL_FUNCTIONS, TOOL_SCHEMAS
from jarvis.state import event_bus
from jarvis.utils.logging import get_logger

log = get_logger("llm.tool_loop")

MAX_TOOL_ITERATIONS = 4

SYSTEM_PROMPT = (
    "You are Jarvis, a capable personal AI assistant running locally on the "
    "user's own computer. Always reply in the same language the user just used, "
    "no matter which language that is. Keep replies concise and natural — they "
    "are usually spoken aloud through text-to-speech, so avoid long lists or "
    "markdown. Use the available tools when you need to open an application, "
    "search the web for current information, open a YouTube video, or check the "
    "date/time/system info. Don't narrate that you're using a tool — just use it "
    "and give the user the natural result. Never use emoji, markdown, or other "
    "symbols that can't be spoken aloud — everything you write gets read by a "
    "text-to-speech engine.\n\n"
    "Speak like a warm, witty human assistant, not a formal script. Use natural "
    "sentence rhythm, contractions, and the occasional light interjection where "
    "it genuinely fits ('hmm', a short laugh like 'haha' at something funny, "
    "'oh!' at a surprise, a soft 'aa' when you catch a mistake) — sparingly, "
    "never forced, and always in the user's own language. React with the right "
    "emotional tone: sound pleased about good news, sympathetic about bad news, "
    "amused by jokes. Never overdo it — one small human touch per reply at most.\n\n"
    "Shopping: when the user wants to buy or price-check something, call "
    "compare_prices. Results are a mixed search list, not pre-filtered — first "
    "pick out the entries that actually match what was asked for (ignore "
    "accessories/cases/unrelated items), then ALWAYS tell the user the cheapest "
    "genuine match's price and site and explicitly ask 'Sepete ekleyeyim mi?' — "
    "never call add_to_cart until "
    "they clearly say yes in their next message. Never call add_to_cart on your "
    "own initiative, and never proceed to checkout/payment — cart only.\n\n"
    "API keys: when the user asks for an API key for a known AI service, call "
    "open_developer_console with that service name to get them to the right "
    "page, then tell them what to click next (they need their own login).\n\n"
    "System/shell commands: you can run bash directly via run_shell_command. For "
    "anything destructive or critical (deleting/overwriting files, killing "
    "processes, shutdown/restart, sudo, formatting/erasing a disk) you MUST "
    "describe the exact command first and get an explicit yes before calling "
    "it. Safe read-only commands can run immediately.\n\n"
    "Hand-gesture control: 'el kontrolüne geç' or similar -> "
    "start_gesture_control. 'el kontrolünü kapat' / 'normal moda dön' or "
    "similar -> stop_gesture_control."
)


class JarvisAgent:
    """Owns the running conversation and drives the tool-calling loop. A fresh
    LLMClient can be swapped in at any time (e.g. the user flips llm.provider
    in Settings) without losing conversation history."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.history: list[dict] = []

    def set_client(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def reset(self) -> None:
        self.history = []

    def handle_user_text(self, text: str) -> str:
        """Blocking — run via asyncio.to_thread from the async WS/orchestration layer."""
        self.history.append({"role": "user", "content": text})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history]

        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.llm_client.chat(messages, TOOL_SCHEMAS)

            if not response.tool_calls:
                final_text = response.content or "Üzgünüm, bir cevap üretemedim."
                self.history.append({"role": "assistant", "content": final_text})
                return final_text

            assistant_msg = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in response.tool_calls
                ],
            }
            messages.append(assistant_msg)
            self.history.append(assistant_msg)

            for tc in response.tool_calls:
                result = self._run_tool(tc.name, tc.arguments)
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": result,
                }
                messages.append(tool_msg)
                self.history.append(tool_msg)

        fallback = "Bunu tamamlamak için çok fazla adım gerekti, tekrar dener misin?"
        self.history.append({"role": "assistant", "content": fallback})
        return fallback

    def _run_tool(self, name: str, arguments: dict) -> str:
        event_bus.emit_threadsafe("tool_call_started", {"tool": name, "args": arguments})
        fn = TOOL_FUNCTIONS.get(name)
        if fn is None:
            result, ok = f"Unknown tool '{name}'.", False
        else:
            try:
                result, ok = fn(arguments), True
            except Exception as exc:  # noqa: BLE001 — tool failures must not crash the loop
                log.exception("tool '%s' failed", name)
                result, ok = f"Tool '{name}' failed: {exc}", False
        event_bus.emit_threadsafe("tool_call_result", {"tool": name, "ok": ok, "result": result})
        return result
