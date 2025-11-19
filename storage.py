# storage.py
import json
import os


def load_seen(path: str) -> set:
    """
    Charge un fichier JSON contenant une liste de strings et
    renvoie un set(). Gère fichier manquant, vide ou corrompu.
    """
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # Fichier corrompu ou illisible : on repart de zéro
        return set()

    if isinstance(data, list):
        return set(data)
    return set()


def save_seen(path: str, seen: set) -> None:
    """
    Sauvegarde un set() sous forme de liste JSON.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(seen)), f, indent=2, ensure_ascii=False)
