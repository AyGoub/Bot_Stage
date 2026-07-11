"""
Source APEC — API JSON interne (non documentée officiellement).

apec.fr affiche ses résultats de recherche via un composant Angular côté
client ; le HTML brut ne contient donc aucune offre. En observant le
trafic réseau de la page /candidat/recherche-stage.html (recherche stage
dédiée), on identifie l'appel suivant, accessible directement en HTTP,
sans session ni cookie :

    POST https://www.apec.fr/cms/webservices/rechercheOffre
    Content-Type: application/json
    body: voir _build_search_body() ci-dessous

Le code typesContrat=597171 correspond à "Stage" (déduit de la page
recherche-stage.html ; à re-vérifier si APEC change son référentiel et
que les résultats redeviennent vides ou incohérents).
"""
import logging
import time

import requests

from config import APEC_LOCATION_FILTER, APEC_SEARCH_TERMS

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.apec.fr/cms/webservices/rechercheOffre"
DETAIL_URL_TEMPLATE = "https://www.apec.fr/candidat/recherche-emploi.html/emploi/detail-offre/{numero}"

STAGE_TYPE_CONTRAT = 597171

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://www.apec.fr/candidat/recherche-stage.html/stage",
}

PAGE_SIZE = 20
MAX_RESULTS_PER_TERM = 200  # garde-fou anti-boucle infinie
REQUEST_DELAY_SECONDS = 1.0  # délai raisonnable entre requêtes


def _build_search_body(mots_cles, start_index):
    return {
        "lieux": APEC_LOCATION_FILTER,
        "fonctions": [],
        "statutPoste": [],
        "typesContrat": [STAGE_TYPE_CONTRAT],
        "typesConvention": [],
        "niveauxExperience": [],
        "idsEtablissement": [],
        "secteursActivite": [],
        "typesTeletravail": [],
        "idNomZonesDeplacement": [],
        "positionNumbersExcluded": [],
        "typeClient": "CADRE",
        "sorts": [{"type": "SCORE", "direction": "DESCENDING"}],
        "pagination": {"range": PAGE_SIZE, "startIndex": start_index},
        "activeFiltre": True,
        "pointGeolocDeReference": {"distance": 0},
        "motsCles": mots_cles,
    }


def _search_one_term(mots_cles):
    offers_by_id = {}
    start = 0

    while start < MAX_RESULTS_PER_TERM:
        body = _build_search_body(mots_cles, start)
        resp = requests.post(SEARCH_URL, json=body, headers=HEADERS, timeout=20)

        if resp.status_code == 429:
            logger.warning("APEC: 429 rate limited, pause 5s")
            time.sleep(5)
            continue
        resp.raise_for_status()

        data = resp.json()
        results = data.get("resultats", [])
        for r in results:
            offers_by_id[r["id"]] = r

        if len(results) < PAGE_SIZE:
            break

        start += PAGE_SIZE
        time.sleep(REQUEST_DELAY_SECONDS)

    return offers_by_id


def fetch_offers():
    all_offers = {}
    for term in APEC_SEARCH_TERMS:
        if not term or not term.strip():
            continue
        try:
            all_offers.update(_search_one_term(term))
        except Exception:
            logger.exception("APEC: échec de la recherche pour le terme %r", term)
        time.sleep(REQUEST_DELAY_SECONDS)

    normalized = []
    for offer_id, o in all_offers.items():
        numero = o.get("numeroOffre") or str(offer_id)
        normalized.append({
            "id": f"apec:{offer_id}",
            "source": "apec",
            "title": o.get("intitule", ""),
            "company": o.get("nomCommercial") or "Entreprise non précisée",
            "city": o.get("lieuTexte", ""),
            "url": DETAIL_URL_TEMPLATE.format(numero=numero),
            "published_date": o.get("datePublication"),
            "description": o.get("texteOffre", ""),
        })
    return normalized
