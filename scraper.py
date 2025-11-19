import requests
from bs4 import BeautifulSoup
import json
import os

URL = "https://www.ldplayer.net/blog/clash-of-clans-codes.html"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_COC")


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
    data = {
        "content": f"🎉 Nouveau code Clash of Clans détecté !\n**{item['text']}**\nLien : {item['link']}"
    }
    requests.post(WEBHOOK_URL, json=data, timeout=10)


def load_seen():
    if not os.path.exists("seen.json"):
        return set()

    with open("seen.json", "r") as f:
        return set(json.load(f))


def save_seen(seen):
    with open("seen.json", "w") as f:
        json.dump(list(seen), f, indent=2)


def main():
    if not WEBHOOK_URL:
        print("Missing DISCORD_WEBHOOK_COC environment variable.")
        return

    seen = load_seen()
    codes = fetch_codes()

    new_items = []
    for c in codes:
        identifier = c["text"] + "|" + c["link"]
        if identifier not in seen:
            new_items.append(c)
            seen.add(identifier)

    if new_items:
        for item in new_items:
            notify_discord(item)
        save_seen(seen)
        print(f"{len(new_items)} nouveaux codes détectés.")
    else:
        print("Aucun nouveau code.")


if __name__ == "__main__":
    main()
