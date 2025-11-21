# scraper_clashRoyale.py
import os
import requests
from bs4 import BeautifulSoup

from storage import load_seen, save_seen
from qrdecode import decode_qr_from_url

URL = "https://www.pockettactics.com/clash-royale/codes"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
# Ensure we always read/write the seen file next to this script
SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen_clashRoyale.json")


def fetch_qr_codes():
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    
    # Trouve le h2 en vérifiant son texte complet (avec get_text)
    heading = None
    for h2 in soup.find_all("h2"):
        if "qr code" in h2.get_text().lower():
            heading = h2
            break
    
    if not heading:
        print("Section 'Clash Royale QR codes' non trouvée.")
        return results

    print(f"✓ Section trouvée : {heading.get_text(strip=True)}")
    
    # Parcourir les éléments suivants
    for tag in heading.find_all_next():
        if tag.name == "h2":
            break

        if tag.name == "p":
            strong = tag.find("strong")
            if strong and "Reward:" in strong.get_text():
                full_text = tag.get_text(" ", strip=True)
                reward = full_text.replace("Reward:", "").strip()

                # Trouver l'image QR dans le <p> précédent
                img_url = None
                prev = tag.find_previous_sibling("p")
                while prev and not img_url:
                    img = prev.find("img")
                    if img and img.get("src"):
                        img_url = img["src"]
                        break
                    prev = prev.find_previous_sibling("p")

                if img_url:
                    decoded_url = decode_qr_from_url(img_url)
                    results.append(
                        {
                            "reward": reward,
                            "image": img_url,
                            "qr_url": decoded_url,
                        }
                    )
                    print(f"  → QR trouvé : {reward}")

    return results


def notify_discord(item):
    data = {
        "content": (
            "🃏 Nouveau QR code Clash Royale détecté !\n"
            f"**Reward : {item['reward']}**\n"
            f"QR : {item['qr_url']}\n"
            # f"Image : {item['image']}"
        )
    }
    requests.post(WEBHOOK_URL, json=data, timeout=10)


def main():
    if not WEBHOOK_URL:
        print("Missing DISCORD_WEBHOOK")
        return

    seen = load_seen(SEEN_FILE)
    print(f"🔎 Loaded seen file: {SEEN_FILE} ({len(seen)} items)")
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
        print(f"🔧 Saving seen file: {SEEN_FILE}")
        save_seen(SEEN_FILE, seen)
        print(f"{len(new_items)} QR codes Clash Royale détectés.")
    else:
        print("Aucun nouveau QR code.")


if __name__ == "__main__":
    main()