import re

from jarvis.utils.logging import get_logger

log = get_logger("tools.add_to_cart")

# Deliberately only matches "add to cart" style phrasing — never "buy now" /
# "satın al" / "hemen al", which would skip the cart and risk starting an
# actual checkout/payment flow. This tool must only ever be called after the
# user has explicitly confirmed the price+site (see compare_prices SCHEMA and
# the system prompt) — it does not ask for confirmation itself.
ADD_TO_CART_PATTERN = re.compile(
    r"sepete\s*ekle|add\s*to\s*(cart|bag|basket)", re.IGNORECASE
)

SCHEMA = {
    "type": "function",
    "function": {
        "name": "add_to_cart",
        "description": (
            "Open a product page and click its 'add to cart' button. Only call this "
            "AFTER the user has explicitly confirmed (yes/add it/get it) a specific "
            "price+site you already presented from compare_prices. Never calls "
            "checkout/buy-now — cart only."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The exact product page URL to open."}
            },
            "required": ["url"],
        },
    },
}


def run(args: dict) -> str:
    from jarvis.browser.controller import controller

    url = args["url"]
    page = controller.new_page()
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        candidates = page.locator("button, a[role=button], input[type=submit]").all()
        for el in candidates[:200]:
            try:
                text = el.inner_text().strip()
            except Exception:
                continue
            if text and ADD_TO_CART_PATTERN.search(text):
                el.click(timeout=5000)
                page.wait_for_timeout(1000)
                return f"'{text}' butonuna tıklandı, ürün sepete eklendi. Sayfa açık kaldı, kontrol edebilirsin."

        return (
            "Sayfada otomatik tıklayabileceğim bir 'sepete ekle' butonu bulamadım — "
            "sayfayı senin için açık bıraktım, oradan elle ekleyebilirsin."
        )
    finally:
        pass  # leave the page open so the user can see/complete the cart
