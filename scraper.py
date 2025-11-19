import requests
from bs4 import BeautifulSoup
import json
import os
import sys
from datetime import datetime
from pathlib import Path

URL = "https://www.ldplayer.net/blog/clash-of-clans-codes.html"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_COC")
SEEN_FILE = Path("seen.json")
MAX_RETRIES = 3
TIMEOUT = 15


def log(message):
    """Log avec timestamp"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")


def fetch_codes():
    """Récupère les codes depuis la page web avec retry"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"🌐 Tentative {attempt}/{MAX_RETRIES} de récupération des codes...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(URL, timeout=TIMEOUT, headers=headers)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            
            for p in soup.find_all("p"):
                a = p.find("a", href=True, text="Reward Link")
                if a:
                    text = p.get_text().strip()
                    href = a["href"]
                    results.append({"text": text, "link": href})
            
            log(f"✅ {len(results)} codes trouvés sur la page")
            return results
            
        except requests.Timeout:
            log(f"⏱️  Timeout lors de la tentative {attempt}")
            if attempt == MAX_RETRIES:
                log("❌ Échec après tous les essais (timeout)")
                return []
                
        except requests.RequestException as e:
            log(f"❌ Erreur réseau tentative {attempt}: {e}")
            if attempt == MAX_RETRIES:
                log("❌ Échec après tous les essais (erreur réseau)")
                return []
                
        except Exception as e:
            log(f"❌ Erreur inattendue: {e}")
            return []
    
    return []


def notify_discord(item, is_test=False):
    """Envoie une notification Discord avec retry"""
    if not WEBHOOK_URL:
        log("⚠️  Webhook Discord non configuré")
        return False
    
    prefix = "🧪 [TEST]" if is_test else "🎉"
    data = {
        "content": f"{prefix} Nouveau code Clash of Clans détecté !\n**{item['text']}**\nLien : {item['link']}"
    }
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(WEBHOOK_URL, json=data, timeout=TIMEOUT)
            resp.raise_for_status()
            log(f"✉️  Notification envoyée avec succès")
            return True
        except Exception as e:
            log(f"⚠️  Échec envoi Discord tentative {attempt}: {e}")
            if attempt == MAX_RETRIES:
                log("❌ Impossible d'envoyer la notification Discord")
                return False
    
    return False


def load_seen():
    """Charge les codes déjà vus"""
    if not SEEN_FILE.exists():
        log("📄 Création d'un nouveau fichier seen.json")
        return set()
    
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            log(f"📋 {len(data)} codes déjà vus chargés")
            return set(data)
    except json.JSONDecodeError:
        log("⚠️  Fichier seen.json corrompu, réinitialisation")
        return set()
    except Exception as e:
        log(f"❌ Erreur lecture seen.json: {e}")
        return set()


def save_seen(seen):
    """Sauvegarde les codes vus"""
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(seen)), f, indent=2, ensure_ascii=False)
        log(f"💾 {len(seen)} codes sauvegardés dans seen.json")
        return True
    except Exception as e:
        log(f"❌ Erreur sauvegarde seen.json: {e}")
        return False


def send_heartbeat():
    """Envoie un heartbeat pour confirmer que le script tourne"""
    if not WEBHOOK_URL:
        return
    
    try:
        data = {
            "content": f"💚 Scraper actif - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        requests.post(WEBHOOK_URL, json=data, timeout=TIMEOUT)
    except:
        pass


def main():
    log("🚀 Démarrage du scraper Clash of Clans")
    
    # Vérification de la configuration
    if not WEBHOOK_URL:
        log("❌ Variable d'environnement DISCORD_WEBHOOK_COC manquante")
        sys.exit(1)
    
    # Envoie un heartbeat toutes les 10 exécutions (pour vérifier que ça tourne)
    if os.path.exists("run_count.txt"):
        with open("run_count.txt", "r") as f:
            count = int(f.read().strip() or "0")
    else:
        count = 0
    
    count += 1
    with open("run_count.txt", "w") as f:
        f.write(str(count))
    
    if count % 10 == 0:
        send_heartbeat()
    
    # Charge les codes déjà vus
    seen = load_seen()
    
    # Récupère les codes actuels
    codes = fetch_codes()
    
    if not codes:
        log("⚠️  Aucun code récupéré (site inaccessible ou erreur)")
        sys.exit(0)
    
    # Détecte les nouveaux codes
    new_items = []
    for c in codes:
        identifier = c["text"] + "|" + c["link"]
        if identifier not in seen:
            new_items.append(c)
            seen.add(identifier)
    
    # Notifie et sauvegarde
    if new_items:
        log(f"✨ {len(new_items)} nouveaux codes détectés !")
        for item in new_items:
            notify_discord(item)
        save_seen(seen)
    else:
        log("✅ Aucun nouveau code (normal si la page n'a pas changé)")
    
    log("🏁 Scraper terminé avec succès")


if __name__ == "__main__":
    main()