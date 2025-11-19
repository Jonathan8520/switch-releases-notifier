# scraper_clashRoyal.py
import os
import requests
from bs4 import BeautifulSoup

from storage import load_seen, save_seen
from qrdecode import decode_qr_from_url

URL = "https://www.pockettactics.com/clash-royale/codes"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SEEN_FILE = "seen_clashRoyal.json"


def fetch_qr_codes():
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    heading = soup.find("h2", string=lambda s: s and "Clash Royale QR codes" in s)
    if not heading:
        print("Section 'Clash Royale QR codes' non trouvée.")
        return results

    for tag in heading.find_all_next():
        if tag.name == "h2":
            break

        if tag.name == "p":
            strong = tag.find("strong")
            if strong and "Reward:" in strong.get_text():
                full_text = tag.get_text(" ", strip=True)
                reward = full_text.replace("Reward:", "").strip()

                # Trouver p précédent contenant l'image QR
                img_url = None
                prev = tag.find_previous_sibling("p")
                while prev and not img_url:
                    img = prev.find("img")
                    if img and img.get("src"):
                        img_url = img["src"]
                        break
                    prev = prev.find_previous_sibling("p")

                if img_url:
                    # 🔥 Decode du QR code !
                    decoded_url = decode_qr_from_url(img_url)

                    results.append(
                        {
                            "reward": reward,
                            "image": img_url,
                            "qr_url": decoded_url,  # l’URL du voucher !
                        }
                    )

    return results


def notify_discord(item):
    data = {
        "content": (
            "🃏 Nouveau QR code Clash Royale détecté !\n"
            f"**Reward : {item['reward']}**\n"
            f"QR : {item['qr_url']}\n"
            f"Image : {item['image']}"
        )
    }
    requests.post(WEBHOOK_URL, json=data, timeout=10)


def main():
    if not WEBHOOK_URL:
        print("Missing DISCORD_WEBHOOK")
        return

    seen = load_seen(SEEN_FILE)
    qr_codes = fetch_qr_codes()

    new_items = []
    for item in qr_codes:
        identifier = f"CR|{item['reward']}|{item['qr_url']}"
        if identifier not in seen:
            new_items.append(item)
            seen.add(identifier)

    if new_items:
        for item in new_items:
            notify_discord(item)
        save_seen(SEEN_FILE, seen)
        print(f"{len(new_items)} QR codes Clash Royale détectés.")
    else:
        print("Aucun nouveau QR code.")


if __name__ == "__main__":
    main()