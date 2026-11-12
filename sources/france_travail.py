"""
Source France Travail (ex Pôle Emploi) — API officielle "Offres d'emploi v2".

Documentation : https://francetravail.io/produits-partenaires/catalogue/offres-emploi-v2
Authentification OAuth2 client_credentials, scope api_offresdemploiv2.

Identifiants attendus dans les variables d'environnement :
  - FRANCE_TRAVAIL_CLIENT_ID
  - FRANCE_TRAVAIL_CLIENT_SECRET

Filtre contrat : on passe typeContrat=CDI directement à l'API (code
présent dans le référentiel GET .../v2/referentiel/typesContrats). France
Travail ne couvre que la France.
"""
import logging
import os
import time

import requests

from config import FRANCE_TRAVAIL_LOCATION_PARAMS, FRANCE_TRAVAIL_SEARCH_TERMS

logger = logging.getLogger(__name__)

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

PAGE_SIZE = 150  # taille de page maximale autorisée par l'API (range 0-149)
MAX_RESULTS_PER_TERM = 600  # garde-fou anti-boucle infinie
REQUEST_DELAY_SECONDS = 0.4  # respecte les limites de débit de l'API

CONTRACT_TYPE = "CDI"

_token_cache = {"access_token": None, "expires_at": 0}


def _get_access_token(client_id, client_secret):
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 30:
        return _token_cache["access_token"]

    scope = f"application_{client_id} api_offresdemploiv2 o2dsoffre"
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 1500)
    return _token_cache["access_token"]


def _search_one_term(token, mots_cles):
    headers = {"Authorization": f"Bearer {token}"}
    offers_by_id = {}
    start = 0

    while start < MAX_RESULTS_PER_TERM:
        params = {
            "motsCles": mots_cles,
            "typeContrat": CONTRACT_TYPE,
            **FRANCE_TRAVAIL_LOCATION_PARAMS,
        }
        req_headers = dict(headers)
        req_headers["Range"] = f"offres={start}-{start + PAGE_SIZE - 1}"

        resp = requests.get(SEARCH_URL, headers=req_headers, params=params, timeout=20)

        if resp.status_code == 429:
            logger.warning("France Travail: 429 rate limited, pause 5s")
            time.sleep(5)
            continue
        if resp.status_code == 204:
            break
        if resp.status_code not in (200, 206):
            resp.raise_for_status()

        data = resp.json()
        results = data.get("resultats", [])
        for r in results:
            offers_by_id[r["id"]] = r

        if resp.status_code == 200 or not results:
            break

        content_range = resp.headers.get("Content-Range", "")
        total = None
        if "/" in content_range:
            try:
                total = int(content_range.rsplit("/", 1)[-1])
            except ValueError:
                total = None

        start += PAGE_SIZE
        if total is not None and start >= total:
            break

        time.sleep(REQUEST_DELAY_SECONDS)

    return offers_by_id


def fetch_offers():
    client_id = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID")
    client_secret = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "FRANCE_TRAVAIL_CLIENT_ID / FRANCE_TRAVAIL_CLIENT_SECRET manquants "
            "(variables d'environnement non définies)"
        )

    token = _get_access_token(client_id, client_secret)

    all_offers = {}
    for term in FRANCE_TRAVAIL_SEARCH_TERMS:
        if not term or not term.strip():
            continue
        try:
            all_offers.update(_search_one_term(token, term))
        except Exception:
            logger.exception("France Travail: échec de la recherche pour le terme %r", term)
        time.sleep(REQUEST_DELAY_SECONDS)

    normalized = []
    for offer_id, o in all_offers.items():
        if o.get("typeContrat") and o["typeContrat"] != CONTRACT_TYPE:
            continue
        entreprise = o.get("entreprise") or {}
        lieu = o.get("lieuTravail") or {}
        origine = o.get("origineOffre") or {}
        normalized.append({
            "id": f"france_travail:{offer_id}",
            "source": "france_travail",
            "title": o.get("intitule", ""),
            "company": entreprise.get("nom") or "Entreprise non précisée",
            "city": lieu.get("libelle", ""),
            "url": origine.get("urlOrigine")
            or f"https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}",
            "published_date": o.get("dateCreation"),
            "description": o.get("description", ""),
        })
    return normalized
