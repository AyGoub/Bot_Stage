"""
Bot de veille stages PFE en cybersécurité offensive (pentest / red team).

Orchestration : interroge chaque source, filtre les offres pertinentes,
déduplique via seen_offers.json, et notifie les nouveautés sur Discord.
"""
import logging
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import notifier
from config import is_relevant
from sources import apec, france_travail, linkedin, wttj
from storage import load_seen, mark_seen, save_seen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

SOURCES = [
    ("france_travail", france_travail.fetch_offers),
    ("apec", apec.fetch_offers),
    ("linkedin", linkedin.fetch_offers),
    ("wttj", wttj.fetch_offers),
]


def collect_offers():
    all_offers = []
    for name, fetch_fn in SOURCES:
        try:
            offers = fetch_fn()
            logger.info("%s: %d offre(s) récupérée(s)", name, len(offers))
            all_offers.extend(offers)
        except Exception:
            logger.exception("%s: échec de la récupération, source ignorée pour ce run", name)
    return all_offers


def main():
    seen = load_seen()
    offers = collect_offers()

    relevant = [o for o in offers if is_relevant(o.get("title", ""), o.get("description", ""))]
    logger.info("%d offre(s) pertinente(s) sur %d récupérée(s) au total", len(relevant), len(offers))

    new_count = 0
    seen_changed = False
    for offer in relevant:
        if offer["id"] in seen:
            continue
        try:
            notifier.send_offer(offer)
        except Exception:
            logger.exception("Échec de la notification Discord pour %s, retentée au prochain run", offer["id"])
            continue
        mark_seen(seen, offer["id"])
        seen_changed = True
        new_count += 1

    if seen_changed:
        save_seen(seen)
        logger.info("seen_offers.json mis à jour : %d nouvelle(s) offre(s) notifiée(s)", new_count)
    else:
        logger.info("Aucune nouvelle offre pertinente cette fois-ci")


if __name__ == "__main__":
    main()
