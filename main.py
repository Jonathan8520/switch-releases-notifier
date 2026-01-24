import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar

import requests

T = TypeVar("T")

# --- Constants & globals ---

NEWLINE = "\n"
TITLE_ID_BASE_MASK = 0xFFFFFFFFFFFFE000
# On reste proche de ton main.py : TitleID commence par 0100...
TITLE_ID_REGEX = re.compile(r"0100[0-9A-FX]{12}", re.IGNORECASE)

CACHE: Dict[str, Dict[str, Any]] = {
    "releases": {},
    "nfos": {},
}

# srrdb endpoints
SRRDB_SCAN_URL = "https://api.srrdb.com/v1/search/category:nsw/order:date-desc"
SRRDB_RELEASE_URL = "https://api.srrdb.com/v1/details/{release_name}"
SRRDB_FILE_URL = "https://www.srrdb.com/download/file/{release_name}/{file_name}"
SRRDB_ADD_URL = "https://www.srrdb.com/download/temp/{release_name}/{add_id}/{file_name}"

# Tinfoil: image (cover) uniquement
TINFOIL_IMAGE_URL = "https://tinfoil.media/ti/{title_id}/1024/1024/"

# Discord
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
if not DISCORD_WEBHOOK:
    raise RuntimeError("DISCORD_WEBHOOK environment variable is not set")

# Fichier qui mémorise les releases déjà envoyées
SEEN_FILE = Path("seen_releases.json")


# --- Utils persistance ---

def load_seen() -> set:
    """
    Charge la liste des releases déjà envoyées depuis seen_releases.json.
    On stocke les NOMS de release (pas de hash) pour que ce soit lisible.
    """
    if not SEEN_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return set(data)
    except Exception:
        return set()


def save_seen(seen: set) -> None:
    SEEN_FILE.write_text(
        json.dumps(sorted(list(seen)), indent=2),
        encoding="utf-8",
    )


# --- HTTP / srrdb ---

def request_url(
    url: str,
    caller_name: str,
    method: str = "get",
    default: Any = None,
    apply: Optional[str] = None,
    apply_kwargs: Optional[dict] = None,
    return_status_code: bool = False,
    **kwargs: Any,
):
    apply_kwargs = apply_kwargs or {}
    try:
        response: requests.Response = getattr(requests, method)(url, timeout=10, **kwargs)
    except requests.RequestException as exc:
        print(f"[REQ][{caller_name}] error reaching {url}: {exc}")
        return default if not return_status_code else getattr(exc, "response", None).status_code

    if response.status_code not in range(200, 300):
        print(f"[REQ][{caller_name}] non-2xx: {response.status_code} - {response.text[:200]}")
        return default if not return_status_code else response.status_code

    return getattr(response, apply)(**apply_kwargs) if apply else response


def scan_srrdb() -> List[dict]:
    data = request_url(SRRDB_SCAN_URL, "SCN", apply="json")
    if not data:
        return []
    return data.get("results", [])


def find_first_true(iterable: Iterable[T], func: Callable[[T], bool], default: Optional[T] = None) -> Optional[T]:
    for item in iterable:
        if func(item):
            return item
    return default


def get_details(release_name: str) -> Optional[dict]:
    if release_name in CACHE["releases"]:
        return CACHE["releases"][release_name]

    details = request_url(
        SRRDB_RELEASE_URL.format(release_name=release_name),
        "DET",
        apply="json",
    )
    CACHE["releases"][release_name] = details
    return details


# --- TitleID / NFO / Tinfoil ---

def mask_title_id(title_id: str) -> str:
    """
    Transforme n'importe quel TitleID (base / update / DLC) en TitleID "base"
    pour l'image Tinfoil et l'URL eShop.

    Exemples:
      0100C6B010FD6800 -> 0100C6B010FD6000
      01002A201FD4B000 -> 01002A201FD4A000
      01008FE00E2F7000 -> 01008FE00E2F6000
      0100EF80230AF001 -> 0100EF80230AE000
    """
    return "0" + hex(int(title_id, 16) & TITLE_ID_BASE_MASK)[2:].upper()


def parse_nfo(nfo_url: str) -> Optional[Tuple[str, str]] | int:
    """
    Télécharge l'NFO, extrait le TitleID et calcule le TitleID masqué/base.
    Retourne :
      (title_id, masked_title_id) en cas de succès
      int (code HTTP) en cas d'erreur HTTP
      None si pas de TitleID trouvé
    """
    print(f"[NFO] Parsing {nfo_url}")
    nfo = request_url(nfo_url, "NFO", return_status_code=True)

    if isinstance(nfo, int) or not nfo:
        return nfo

    nfo_text = nfo.content.decode("cp437")
    title_id = TITLE_ID_REGEX.search(nfo_text)

    if not title_id:
        print(f"[NFO] Could not parse Title ID from {nfo_url}")
        return None

    title_id = title_id.group().replace("X", "0")
    masked_title_id = mask_title_id(title_id)

    if title_id not in CACHE["nfos"]:
        CACHE["nfos"][title_id] = nfo_text

    return title_id, masked_title_id


def humansize(size: int) -> str:
    suffixes = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    index = 0

    size = float(size)
    while size >= 1024 and index < len(suffixes) - 1:
        size /= 1024.0
        index += 1

    size_str = ("%.2f" % size).rstrip("0").rstrip(".")
    return f"{size_str} {suffixes[index]}"


def get_info(release_name: str) -> Optional[Dict[str, Any]] | int:
    """
    Récupère les infos complètes d'une release :
    - proof URL
    - NFO URL
    - TitleID & TitleID masqué/base
    - taille humaine
    - CRC
    - URL de thumb Tinfoil (avec TitleID masqué)
    """
    details = get_details(release_name)
    if not details:
        return None

    proof_url = None
    files = details["files"]

    maybe_proof = find_first_true(
        files, lambda f: "Proof/" in f["name"] and f["name"].endswith(".jpg")
    )

    if maybe_proof:
        proof_url = SRRDB_FILE_URL.format(
            release_name=release_name, file_name=maybe_proof["name"]
        )

    nfo_file = find_first_true(files, lambda f: f["name"].endswith(".nfo"))

    if not nfo_file and not details.get("adds"):
        return None

    if nfo_file:
        nfo_url = SRRDB_FILE_URL.format(
            release_name=release_name, file_name=nfo_file["name"]
        )

    if details.get("adds"):
        nfo_file = find_first_true(
            details["adds"], lambda f: f["name"].endswith(".nfo")
        )
        if nfo_file:
            nfo_url = SRRDB_ADD_URL.format(
                release_name=release_name,
                add_id=nfo_file["id"],
                file_name=nfo_file["name"],
            )

    if not nfo_file:
        return None

    parse_result = parse_nfo(nfo_url)
    if isinstance(parse_result, int):
        # code HTTP (404, 429, etc.)
        return parse_result
    if not parse_result:
        return None

    title_id, masked_title_id = parse_result

    size = humansize(details["archived-files"][0]["size"])
    crc = details["archived-files"][0]["crc"]

    return {
        "tid": title_id,
        "masked_tid": masked_title_id,
        "title": release_name,
        "size": size,
        "crc": crc,
        "proof": proof_url,
        "nfo": nfo_url,
        "thumb": TINFOIL_IMAGE_URL.format(title_id=masked_title_id),
    }


# --- Discord helpers ---

# Couleurs par type
COLORS = {
    "Base": 0x2ECC71,    # Vert
    "Update": 0x3498DB,  # Bleu
    "DLC": 0x9B59B6,     # Violet
}

# Emojis par type
EMOJIS = {
    "Base": "🎮",
    "Update": "🔄",
    "DLC": "📦",
}


def detect_type_from_title(title: str) -> str:
    """
    Détection rapide à partir du nom :
    - 'DLC', 'DLC_Unlocker' etc. -> DLC
    - 'Update', '.UPDATE.', 'UPD' -> Update
    - sinon                       -> Base
    """
    t = title.upper().replace("_", " ")

    if " DLC " in t or t.endswith(" DLC") or "DLC " in t or " DLC_" in t or " UNLOCKER" in t:
        return "DLC"

    if " UPDATE " in t or ".UPDATE." in t or " UPD" in t:
        return "Update"

    return "Base"


def extract_group(title: str) -> str:
    """
    Extrait le groupe à la fin du nom :
    '...NSW-VENOM' -> 'VENOM'
    """
    if "-" not in title:
        return "Unknown"
    return title.rsplit("-", 1)[1]


def extract_version(title: str) -> Optional[str]:
    """
    Extrait la version d'un titre.
    'Pokemon_Legends_Z-A_Update_v2.0.1_NSW-VENOM' -> 'v2.0.1'
    """
    match = re.search(r'[_\s](v\d+(?:\.\d+)*)', title, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extract_clean_name(title: str) -> str:
    """
    Extrait le nom propre du jeu.
    'Pokemon_Legends_Z-A_Update_v2.0.1_NSW-VENOM' -> 'Pokemon Legends Z-A'
    """
    name = title

    # Retirer le groupe à la fin (NSW-VENOM)
    if "-" in name:
        name = name.rsplit("-", 1)[0]

    # Retirer _NSW ou _NSW_ si présent
    name = re.sub(r'_NSW_?$', '', name, flags=re.IGNORECASE)

    # Retirer la version (v1.0.0, v2.1.3, etc.)
    name = re.sub(r'_v\d+(?:\.\d+)*', '', name, flags=re.IGNORECASE)

    # Retirer Update/UPD
    name = re.sub(r'_(?:Update|UPD)_?', '', name, flags=re.IGNORECASE)

    # Retirer DLC/DLC_Unlocker
    name = re.sub(r'_(?:DLC(?:_Unlocker)?)', '', name, flags=re.IGNORECASE)

    # Remplacer les underscores par des espaces
    name = name.replace("_", " ").strip()

    return name


def build_eshop_url(masked_title_id: str) -> str:
    """
    Construit l'URL eShop à partir du TitleID base (masqué).
    Exemple :
      0100EF80230AE000 -> https://ec.nintendo.com/apps/0100EF80230AE000/FR
    """
    return f"https://ec.nintendo.com/apps/{masked_title_id}/FR"


def build_srrdb_url(release_name: str) -> str:
    """
    Construit l'URL srrDB pour une release.
    """
    return f"https://www.srrdb.com/release/details/{release_name}"


def build_discord_payload(release_info: Dict[str, Any]) -> Dict[str, Any]:
    title = release_info["title"]
    title_id = release_info["tid"]
    masked_tid = release_info["masked_tid"]
    size = release_info["size"]

    release_type = detect_type_from_title(title)
    group = extract_group(title)
    version = extract_version(title)
    clean_name = extract_clean_name(title)

    eshop_url = build_eshop_url(masked_tid)
    srrdb_url = build_srrdb_url(title)

    emoji = EMOJIS.get(release_type, "🎮")
    color = COLORS.get(release_type, 0x00FFE0)

    # Fields pour un layout propre
    fields = []

    if version:
        fields.append({
            "name": "📦 Version",
            "value": f"`{version}`",
            "inline": True
        })

    fields.append({
        "name": "🎮 TitleID",
        "value": f"`{title_id}`",
        "inline": True
    })

    fields.append({
        "name": "💾 Taille",
        "value": f"`{size}`",
        "inline": True
    })

    embed: Dict[str, Any] = {
        "title": f"{emoji} {clean_name}",
        "url": srrdb_url,
        "description": f"[🛒 Voir sur l'eShop]({eshop_url})",
        "color": color,
        "fields": fields,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "thumbnail": {
            "url": release_info["thumb"],
        },
        "footer": {
            "text": group
        }
    }

    return {"embeds": [embed]}


def send_to_discord(payload: Dict[str, Any]) -> bool:
    """
    Envoie sur Discord, retourne True si 2xx, False sinon.
    """
    try:
        resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except requests.RequestException as exc:
        print(f"[DISCORD] request error: {exc}")
        return False

    if resp.status_code not in range(200, 299):
        print(f"[DISCORD] error {resp.status_code}: {resp.text[:200]}")
        return False

    return True


# --- Main: un run (adapté CRON / GitHub Actions) ---

def main() -> None:
    print("[INFO] Scanning srrdb…")

    # Détecte le premier run (fichier inexistant)
    first_run = not SEEN_FILE.exists()
    seen = load_seen()

    releases = scan_srrdb()
    if not releases:
        print("[INFO] No releases returned by srrdb.")
        return

    # Premier run : on marque tout comme vu sans notifier
    if first_run:
        print("[INFO] First run detected - initializing seen_releases.json without notifications.")
        for release in releases:
            seen.add(release["release"])
        save_seen(seen)
        print(f"[INFO] Marked {len(releases)} releases as seen.")
        return

    new_count = 0

    for release in releases:
        name = release["release"]

        if name in seen:
            continue

        if not release.get("hasNFO"):
            print(f"[INFO] {name} has no NFO, skipping.")
            continue

        info = get_info(name)
        if not info or isinstance(info, int):
            print(f"[WARN] Could not get info for {name}: {info}")
            continue

        payload = build_discord_payload(info)
        print(f"[INFO] Sending release to Discord: {name}")
        ok = send_to_discord(payload)

        if ok:
            # On marque comme vu uniquement si l'envoi Discord a réussi
            seen.add(name)
            save_seen(seen)
            new_count += 1
        else:
            print(f"[WARN] Discord send failed for {name}, not marking as seen.")

        # Petit délai pour ne pas spam Discord
        time.sleep(1)

    if new_count == 0:
        print("[INFO] No new releases to send.")
    else:
        print(f"[INFO] Sent {new_count} new release(s).")


if __name__ == "__main__":
    main()
