# scraper_clashOfClans.py
import os
import requests
from bs4 import BeautifulSoup

from storage import load_seen, save_seen

URL = "https://www.ldplayer.net/blog/clash-of-clans-codes.html"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SEEN_FILE = "seen_clashOfClans.json"


def fetch_codes():
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for p in soup.find_all("p"):
        a = p.find("a", href=True, text="Reward Link")
        if a:
            text = p.get_text().strip()
            href = a["href"]
            results.append({"text": text, "link": href})

    return results


def notify_discord(item):
    if not WEBHOOK_URL:
        print("Missing DISCORD_WEBHOOK environment variable.")
        return

    data = {
        "content": (
            "🎉 Nouveau code Clash of Clans détecté !\n"
            f"**{item['text']}**\n"
            f"Lien : {item['link']}"
        )
    }
    requests.post(WEBHOOK_URL, json=data, timeout=10)


def main():
    if not WEBHOOK_URL:
        print("Missing DISCORD_WEBHOOK environment variable.")
        return

    seen = load_seen(SEEN_FILE)
    codes = fetch_codes()

    new_items = []
    for c in codes:
        identifier = f"COC|{c['text']}|{c['link']}"
        if identifier not in seen:
            new_items.append(c)
            seen.add(identifier)

    if new_items:
        for item in new_items:
            notify_discord(item)
        save_seen(SEEN_FILE, seen)
        print(f"{len(new_items)} nouveaux codes Clash of Clans détectés.")
    else:
        print("Aucun nouveau code Clash of Clans.")


if __name__ == "__main__":
    main()
