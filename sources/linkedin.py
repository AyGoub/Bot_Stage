"""
Source LinkedIn — endpoint public "guest" (recherche d'offres sans connexion).

    GET https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
        ?keywords=...&location=...&f_JT=F&start=...

Renvoie du HTML pré-rendu (pas de JS à exécuter), utilisable en simple
requests + BeautifulSoup. f_JT=F filtre sur le type de poste "Full-time"
(LinkedIn ne distingue pas CDI/CDD : le filtre de config.is_relevant exclut
ensuite les titres contenant stage/CDD/freelance/etc.).

Une recherche est faite pour chaque terme ET chaque pays de
config.LINKEDIN_LOCATIONS (France, Suisse, Luxembourg) : c'est la seule
source qui couvre la Suisse et le Luxembourg.

Limites connues :
  - Les cartes de résultats n'exposent que le titre, l'entreprise, la ville
    et la date — pas la description complète. Le filtre de pertinence
    s'applique donc sur le titre seul pour cette source.
  - f_JT n'est pas honoré de façon fiable en accès anonyme (constaté
    auparavant avec f_JT=I) : d'où le filtre défensif sur le titre.
  - LinkedIn bloque plus agressivement les IP de datacenter (runners GitHub
    Actions). En cas de blocage (429/999), la source échoue proprement et
    les autres sources continuent de fonctionner (voir main.py).
  - L'endpoint renvoie toujours 10 résultats par page (PAGE_SIZE = 10).
"""
import logging
import time

import requests
from bs4 import BeautifulSoup

from config import LINKEDIN_LOCATIONS, LINKEDIN_SEARCH_TERMS, is_relevant

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

PAGE_SIZE = 10  # taille de page réelle de l'endpoint, non configurable (voir docstring)
MAX_RESULTS_PER_TERM = 50  # garde-fou (= 5 pages / terme / pays ; requêtes PAM très ciblées)
REQUEST_DELAY_SECONDS = 1.5  # délai raisonnable entre requêtes

def _extract_job_id(urn):
    if urn and ":" in urn:
        return urn.rsplit(":", 1)[-1]
    return urn or None


def _search_one_term(term, location):
    offers = []
    start = 0

    while start < MAX_RESULTS_PER_TERM:
        params = {
            "keywords": term,
            "location": location,
            "f_JT": "F",  # Full-time
            "start": start,
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)

        if resp.status_code in (429, 999):
            logger.warning("LinkedIn: bloqué (%s) pour %r / %r, arrêt", resp.status_code, term, location)
            break
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.job-search-card")
        if not cards:
            break

        for card in cards:
            job_id = _extract_job_id(card.get("data-entity-urn", ""))
            if not job_id:
                continue
            link_tag = card.select_one("a.base-card__full-link")
            title_tag = card.select_one("h3.base-search-card__title")
            company_tag = card.select_one("h4.base-search-card__subtitle")
            location_tag = card.select_one("span.job-search-card__location")
            date_tag = card.select_one("time.job-search-card__listdate")
            title = title_tag.get_text(strip=True) if title_tag else ""
            # Pas de description sur cet endpoint : on filtre tôt sur le
            # titre pour éviter d'accumuler des offres hors sujet.
            if not is_relevant(title):
                continue
            offers.append({
                "id": job_id,
                "title": title,
                "company": company_tag.get_text(strip=True) if company_tag else "",
                "city": location_tag.get_text(strip=True) if location_tag else "",
                "url": link_tag["href"].split("?")[0] if link_tag and link_tag.get("href") else "",
                "published_date": date_tag.get("datetime") if date_tag else None,
            })

        if len(cards) < PAGE_SIZE:
            break

        start += PAGE_SIZE
        time.sleep(REQUEST_DELAY_SECONDS)

    return offers


def fetch_offers():
    all_offers = {}
    for location in LINKEDIN_LOCATIONS:
        for term in LINKEDIN_SEARCH_TERMS:
            if not term or not term.strip():
                continue
            try:
                for o in _search_one_term(term, location):
                    all_offers[o["id"]] = o
            except Exception:
                logger.exception("LinkedIn: échec de la recherche pour %r / %r", term, location)
            time.sleep(REQUEST_DELAY_SECONDS)

    normalized = []
    for offer_id, o in all_offers.items():
        normalized.append({
            "id": f"linkedin:{offer_id}",
            "source": "linkedin",
            "title": o["title"],
            "company": o["company"],
            "city": o["city"],
            "url": o["url"],
            "published_date": o["published_date"],
            "description": "",  # non exposée par l'endpoint de liste
        })
    return normalized
