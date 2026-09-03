from jarvis.system.macos_control import open_url
from jarvis.utils.logging import get_logger

log = get_logger("tools.open_dev_console")

# Opens in the user's real default browser (not the automation profile) since
# creating an API key requires their actual logged-in Google/OpenAI/etc.
# account. Automating clicks through a security-sensitive OAuth console is
# unreliable and trips anti-bot detection — this gets them straight to the
# right page and the model should talk them through the last click or two.
CONSOLE_URLS = {
    "gemini": "https://aistudio.google.com/apikey",
    "google": "https://aistudio.google.com/apikey",
    "openai": "https://platform.openai.com/api-keys",
    "groq": "https://console.groq.com/keys",
    "elevenlabs": "https://elevenlabs.io/app/settings/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "claude": "https://console.anthropic.com/settings/keys",
}

SCHEMA = {
    "type": "function",
    "function": {
        "name": "open_developer_console",
        "description": (
            "Open the official API-key page for a known AI service (Gemini, OpenAI, "
            "Groq, ElevenLabs, Anthropic) in the user's browser, so they can create "
            "or copy an API key. Doesn't create the key itself — talk the user "
            "through the last click since they need to be logged into their own "
            "account."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name, e.g. 'gemini', 'openai', 'groq', 'elevenlabs'.",
                }
            },
            "required": ["service"],
        },
    },
}


def run(args: dict) -> str:
    service = args["service"].strip().lower()
    url = CONSOLE_URLS.get(service)
    if url is None:
        return f"'{service}' için bilinen bir konsol adresim yok."
    open_url(url)
    return f"{service} API anahtarı sayfası açıldı ({url}). Giriş yapıp 'create key' ile anahtarı oluşturup kopyala."
