"""
Configuration éditable du bot de veille CDI — Consultant PAM / CyberArk.

Cible : offres en CDI de consultant / ingénieur PAM (Privileged Access
Management), CyberArk en priorité, en France, en Suisse et au Luxembourg.
Modifiez ce fichier pour ajuster le ciblage (mots-clés, pays, exclusions)
sans toucher au reste du code.
"""
import re

# ---------------------------------------------------------------------------
# Termes de recherche envoyés à chaque source. Une requête est faite par
# terme et par source ; les résultats sont fusionnés puis dédupliqués avant
# d'être passés au filtre de pertinence ci-dessous.
# ---------------------------------------------------------------------------
SEARCH_TERMS = [
    "CyberArk",
    "consultant CyberArk",
    "consultant PAM",
    "ingénieur PAM",
    "PAM cybersécurité",
    "Privileged Access Management",
    "gestion des accès à privilèges",
    "comptes à privilèges",
    "Wallix",
    "Delinea",
    "BeyondTrust",
]

FRANCE_TRAVAIL_SEARCH_TERMS = SEARCH_TERMS
APEC_SEARCH_TERMS = SEARCH_TERMS
LINKEDIN_SEARCH_TERMS = SEARCH_TERMS

# ---------------------------------------------------------------------------
# Filtre géographique.
# ---------------------------------------------------------------------------
# France Travail : France uniquement. Dict fusionné dans les paramètres de
# la requête HTTP, par exemple {"departement": "75"}. Vide = toute la France.
FRANCE_TRAVAIL_LOCATION_PARAMS = {}

# APEC : France uniquement. Liste de codes "lieu" internes APEC (vide =
# toute la France).
APEC_LOCATION_FILTER = []

# LinkedIn : une recherche est faite par pays de cette liste (texte libre
# tel que tapé dans le champ "lieu" de LinkedIn). C'est la source qui
# couvre la Suisse et le Luxembourg.
LINKEDIN_LOCATIONS = ["France", "Switzerland", "Luxembourg"]

# ---------------------------------------------------------------------------
# Filtrage de pertinence (appliqué sur titre + description quand disponible)
# ---------------------------------------------------------------------------

# Une offre est retenue seulement si son texte contient au moins un de ces
# termes (insensible à la casse, mot entier).
INCLUDE_KEYWORDS = [
    "cyberark",
    "pam",
    "privileged access",
    "privileged access management",
    "privileged identity",
    "privileged account",
    "accès à privilèges",
    "acces a privileges",
    "accès privilégiés",
    "acces privilegies",
    "comptes à privilèges",
    "comptes privilégiés",
    "comptes a privileges",
    "comptes privilegies",
    "wallix",
    "delinea",
    "thycotic",
    "beyondtrust",
    "bastion d'administration",
]

# Termes exclus s'ils apparaissent dans le TITRE de l'offre (pas dans la
# description, où "stage", "CDD"... peuvent apparaître dans un CDI, ex:
# "accueil de stagiaires dans l'équipe").
EXCLUDE_TITLE_KEYWORDS = [
    "stage",
    "stagiaire",
    "intern",
    "internship",
    "pfe",
    "alternance",
    "alternant",
    "apprentissage",
    "apprenti",
    "apprenticeship",
    "contrat de professionnalisation",
    "cdd",
    "freelance",
    "free-lance",
    "indépendant",
    "portage",
    "intérim",
    "interim",
    "temporary",
    "fixed-term",
    "fixed term",
    "contractor",
    "volontariat international",
]

# Termes exclus s'ils apparaissent n'importe où (titre + description) :
# ce ne sont clairement pas des CDI.
EXCLUDE_ANYWHERE_KEYWORDS = [
    "contrat de professionnalisation",
    "volontariat international",
    "offre de stage",
    "stage de fin d'études",
    "en alternance",
]

# "VIE" (Volontariat International en Entreprise) en majuscules dans le
# titre ; contrôle sensible à la casse car "vie" est un mot français courant.
_VIE_ACRONYM_RE = re.compile(r"\bVIE\b")

_keyword_pattern_cache = {}


def _keyword_pattern(keywords):
    """Compile (et met en cache) un regex à limites de mots pour une liste
    de mots-clés. Nécessaire pour des mots courts et ambigus comme "pam"
    (sinon il matcherait "pamplemousse", "Pamela"...)."""
    key = tuple(keywords)
    if key not in _keyword_pattern_cache:
        pattern = "|".join(r"\b" + re.escape(kw) + r"\b" for kw in keywords)
        _keyword_pattern_cache[key] = re.compile(pattern, re.IGNORECASE)
    return _keyword_pattern_cache[key]


def _contains_any_keyword(text, keywords):
    return bool(_keyword_pattern(keywords).search(text))


def is_relevant(title, description=""):
    """Applique les filtres INCLUDE/EXCLUDE sur une offre normalisée."""
    title = title or ""
    text = f"{title} {description or ''}"

    if not _contains_any_keyword(text, INCLUDE_KEYWORDS):
        return False

    if _contains_any_keyword(title, EXCLUDE_TITLE_KEYWORDS):
        return False

    if _contains_any_keyword(text, EXCLUDE_ANYWHERE_KEYWORDS):
        return False

    if _VIE_ACRONYM_RE.search(title):
        return False

    return True
