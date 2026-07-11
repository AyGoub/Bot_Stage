"""
Source LinkedIn — endpoint public "guest" (recherche d'offres sans connexion).

    GET https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
        ?keywords=...&location=...&f_JT=I&start=...

Renvoie du HTML pré-rendu (pas de JS à exécuter), utilisable en simple
requests + BeautifulSoup. f_JT=I filtre sur le type de poste "Internship".

Limites connues :
  - Les cartes de résultats n'exposent que le titre, l'entreprise, la ville
    et la date — pas la description complète. Le filtre de pertinence
    (config.is_relevant) s'applique donc surtout sur le titre pour cette
    source, ce qui est plus permissif/plus strict selon les cas que pour
    France Travail ou APEC (où la description complète est disponible).
  - LinkedIn bloque plus agressivement les IP de datacenter (comme celles
    des runners GitHub Actions) que les IP résidentielles. En cas de blocage
    (429/999), la source échoue proprement et les autres sources continuent
    de fonctionner (voir main.py).
  - Le paramètre f_JT=I (type de poste "Internship") n'est PAS honoré de
    façon fiable par cet endpoint en accès anonyme : testé en comparant les
    résultats avec et sans f_JT=I, les mêmes offres en CDI ("Pentester
    confirmé", etc.) reviennent dans les deux cas. On applique donc un
    filtre défensif supplémentaire sur le titre (voir INTERNSHIP_TITLE_HINTS)
    pour ne garder que les intitulés qui ressemblent explicitement à un
    stage, en plus du filtre de durée déjà fait par config.is_relevant.
  - IMPORTANT (bug corrigé le 2026-07-11) : cet endpoint renvoie toujours
    10 résultats par page, quel que soit le paramètre envoyé (testé avec
    count=25/50 : toujours 10). Le code pensait auparavant que la page
    faisait 25, donc il s'arrêtait après la 1ère page (10 < 25) en croyant
    avoir atteint la fin — alors que des offres pertinentes ("Stage de fin
    d'études - Consultant Cybersécurité", vérifié en conditions réelles)
    n'apparaissaient qu'à partir du résultat 50. D'où PAGE_SIZE = 10 et une
    profondeur de pagination augmentée ci-dessous.
"""
import logging
import time

import requests
from bs4 import BeautifulSoup

from config import LINKEDIN_LOCATION, LINKEDIN_SEARCH_TERMS

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
MAX_RESULTS_PER_TERM = 100  # garde-fou anti-boucle infinie (= 10 pages / terme)
REQUEST_DELAY_SECONDS = 1.5  # délai raisonnable entre requêtes

# f_JT=I n'étant pas fiable en anonyme (voir docstring), on exige en plus
# que le titre contienne explicitement un de ces indices de stage.
INTERNSHIP_TITLE_HINTS = ("stage", "stagiaire", "intern", "internship", "pfe")


def _looks_like_internship(title):
    title_lower = (title or "").lower()
    return any(hint in title_lower for hint in INTERNSHIP_TITLE_HINTS)


def _extract_job_id(urn):
    if urn and ":" in urn:
        return urn.rsplit(":", 1)[-1]
    return urn or None


def _search_one_term(term):
    offers = []
    start = 0

    while start < MAX_RESULTS_PER_TERM:
        params = {
            "keywords": term,
            "location": LINKEDIN_LOCATION,
            "f_JT": "I",  # Internship
            "start": start,
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)

        if resp.status_code in (429, 999):
            logger.warning("LinkedIn: bloqué (%s) pour le terme %r, arrêt", resp.status_code, term)
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
            if not _looks_like_internship(title):
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
    for term in LINKEDIN_SEARCH_TERMS:
        if not term or not term.strip():
            continue
        try:
            for o in _search_one_term(term):
                all_offers[o["id"]] = o
        except Exception:
            logger.exception("LinkedIn: échec de la recherche pour le terme %r", term)
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
