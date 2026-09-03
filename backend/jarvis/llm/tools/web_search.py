from jarvis.utils.logging import get_logger

log = get_logger("tools.web_search")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information to answer a question you don't "
            "already know the answer to. Returns titles, snippets and URLs — summarize "
            "them into a natural spoken answer, don't just read the raw results back."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The search query."}},
            "required": ["query"],
        },
    },
}


def run(args: dict) -> str:
    from ddgs import DDGS

    query = args["query"]
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))

    if not results:
        return "No search results found."

    lines = []
    for r in results:
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")
        lines.append(f"- {title}: {body} ({href})")
    return "\n".join(lines)
