from jarvis.utils.logging import get_logger

log = get_logger("tools.compare_prices")

SCHEMA = {
    "type": "function",
    "function": {
        "name": "compare_prices",
        "description": (
            "Search Akakce (Turkish price-comparison site) for a product and return "
            "the top results with price and a purchase link, cheapest first. Use this "
            "when the user wants to buy or price-check something in Turkey. Never call "
            "add_to_cart from this result without first telling the user the "
            "cheapest option's price and getting an explicit yes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The product to search for."}
            },
            "required": ["query"],
        },
    },
}


def run(args: dict) -> str:
    from jarvis.browser.controller import controller

    query = args["query"]
    page = controller.new_page()
    try:
        page.goto(
            f"https://www.akakce.com/arama/?q={query}",
            timeout=20000,
            wait_until="domcontentloaded",
        )
        page.wait_for_timeout(1500)

        cards = page.locator("a.pw_v8").all()
        results = []
        for card in cards[:10]:
            name = card.get_attribute("title")
            price_el = card.locator(".pt_v9")
            if not name or not price_el.count():
                continue
            price = price_el.inner_text().strip().split("\n")[0].replace(" ", "")
            seller = card.locator(
                "xpath=following-sibling::div[contains(@class,'p_w_v9')][1]//a[contains(@class,'iC')][1]"
            )
            href = seller.get_attribute("href") if seller.count() else None
            if not href:
                continue
            results.append((name, price, href))
            if len(results) >= 5:
                break
    finally:
        page.close()

    if not results:
        return f"'{query}' için Akakçe'de sonuç bulunamadı. Farklı bir arama terimi dene."

    lines = [f"{i+1}. {name} — {price} ({href})" for i, (name, price, href) in enumerate(results)]
    return "Fiyat karşılaştırma sonuçları (Akakçe, en ucuzdan sıralı):\n" + "\n".join(lines)
