"""
Welcome to the Jungle — NON IMPLÉMENTÉ.

Investigation menée le 2026-07-11 (requests bruts + navigateur headless
Playwright) : ni le scraping léger ni l'automatisation navigateur ne
permettent de récupérer des résultats de recherche fiables actuellement :

  - Le domaine est protégé par un challenge AWS WAF (statut HTTP 202) qui
    bloque toute requête HTTP simple (confirmé : réponse vide, header
    x-amzn-waf-action: challenge).
  - Même en "réchauffant" les cookies WAF avec un vrai navigateur headless
    (deux navigations successives), la page /fr/jobs?query=...&contract_
    type=internship n'affiche plus une liste de résultats classique : WTTJ
    a remplacé cette page par une interface de "matching" (swipe), qui
    ignore les paramètres de recherche dans l'URL.
  - Leur API interne de résultats (api.welcometothejungle.com/api/v3/
    search/jobs) renvoie 403 Forbidden même depuis une session de
    navigateur légitime ayant passé le challenge WAF — seul l'endpoint de
    comptage (.../search/jobs/count) reste accessible publiquement.

Ce module est laissé en stub pour respecter l'interface commune aux
sources (fetch_offers() -> list). Si WTTJ fait évoluer son site, ou si
vous voulez investir dans une automatisation UI plus lourde (simuler le
flux de matching complet), il faudra probablement repartir de Playwright.
"""
import logging

logger = logging.getLogger(__name__)


def fetch_offers():
    logger.info("WTTJ: source non implémentée (voir docstring du module), retour liste vide")
    return []
