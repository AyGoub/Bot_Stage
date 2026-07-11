"""
Déduplication persistante des offres déjà notifiées.

seen_offers.json est un dict plat { "source:id_offre": "date_ISO_premiere_detection" }.
Chaque clé encode déjà la source (préfixe avant le ":"), ce qui satisfait
le besoin de suivi "par source, ID unique -> date de première détection"
sans imbrication superflue.
"""
import json
import os
from datetime import datetime, timezone

SEEN_OFFERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_offers.json")


def load_seen(path=SEEN_OFFERS_PATH):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen(seen, path=SEEN_OFFERS_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2, sort_keys=True)


def mark_seen(seen, offer_id):
    seen[offer_id] = datetime.now(timezone.utc).isoformat()
