"""Notification Discord via webhook."""
import logging
import os

import requests

logger = logging.getLogger(__name__)

SOURCE_COLORS = {
    "france_travail": 0x0056B3,
    "apec": 0xE4032E,
    "linkedin": 0x0A66C2,
    "wttj": 0xFFCF00,
}

SOURCE_LABELS = {
    "france_travail": "France Travail",
    "apec": "APEC",
    "linkedin": "LinkedIn",
    "wttj": "Welcome to the Jungle",
}


def send_offer(offer):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL non configuré, notification ignorée pour %s", offer["id"])
        return

    source = offer.get("source", "")
    embed = {
        "title": (offer.get("title") or "Offre de stage")[:256],
        "url": offer.get("url") or None,
        "color": SOURCE_COLORS.get(source, 0x2ECC71),
        "fields": [
            {"name": "Entreprise", "value": offer.get("company") or "Non précisée", "inline": True},
            {"name": "Ville", "value": offer.get("city") or "Non précisée", "inline": True},
            {"name": "Source", "value": SOURCE_LABELS.get(source, source), "inline": True},
        ],
    }
    if offer.get("published_date"):
        embed["fields"].append({
            "name": "Publiée le",
            "value": str(offer["published_date"]),
            "inline": True,
        })

    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=15)
    resp.raise_for_status()
