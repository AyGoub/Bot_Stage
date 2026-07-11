"""
Configuration éditable du bot de veille stages cybersécurité offensive.

Modifiez ce fichier pour ajuster le ciblage (mots-clés, ville/région,
durée de stage visée) sans toucher au reste du code.
"""
import re

# ---------------------------------------------------------------------------
# Termes de recherche envoyés à chaque source. Une requête est faite par
# terme et par source ; les résultats sont fusionnés puis dédupliqués avant
# d'être passés au filtre de pertinence ci-dessous.
# ---------------------------------------------------------------------------
SEARCH_TERMS = [
    "pentest",
    "red team",
    "test intrusion",
    "sécurité offensive",
    "ethical hacking",
    "cybersécurité",
    "cybersecurity",
    "penetration test",
    "vulnérabilité",
    "vulnerability",
    "exploitation de vulnérabilités",
    "exploitation de vulnerabilites",

]

FRANCE_TRAVAIL_SEARCH_TERMS = SEARCH_TERMS
APEC_SEARCH_TERMS = SEARCH_TERMS
LINKEDIN_SEARCH_TERMS = SEARCH_TERMS

# ---------------------------------------------------------------------------
# Filtre géographique optionnel. Laissez vide pour couvrir toute la France.
# ---------------------------------------------------------------------------
# France Travail : dict fusionné dans les paramètres de la requête HTTP,
# par exemple {"departement": "75"} ou {"commune": "75101"}.
FRANCE_TRAVAIL_LOCATION_PARAMS = {}

# APEC : liste de codes "lieu" internes APEC. Pour trouver un code, faites
# une recherche sur apec.fr en sélectionnant une ville dans leur filtre
# lieu, et regardez le champ "lieux" envoyé dans la requête réseau vers
# /cms/webservices/rechercheOffre (onglet Réseau des outils dev).
APEC_LOCATION_FILTER = []

# LinkedIn : texte libre, par ex. "Paris" ou "Île-de-France, France".
LINKEDIN_LOCATION = "France"

# ---------------------------------------------------------------------------
# Filtrage de pertinence (appliqué sur titre + description quand disponible)
# ---------------------------------------------------------------------------

# Une offre est retenue seulement si son texte contient au moins un de ces
# termes (recherche insensible à la casse, sous-chaîne simple).
INCLUDE_KEYWORDS = [
    "pentest",
    "pentester",
    "pénétration",
    "penetration",
    "red team",
    "redteam",
    "offensive",
    "ethical hacking",
    "intrusion",
    "exploitation de vulnérabilités",
    "exploitation de vulnerabilites",
]

# Purement indicatif / documentaire : une offre qui ne contient QUE ces
# termes généralistes (sans aucun mot-clé de INCLUDE_KEYWORDS) est de toute
# façon rejetée par le filtre INCLUDE ci-dessus, qui est la seule porte
# d'entrée. Gardé ici pour référence si vous voulez durcir la logique plus
# tard (ex. exclure explicitement même en présence d'un mot-clé offensif).
GENERALIST_ONLY_KEYWORDS = [
    "soc",
    "grc",
    "conformité",
    "conformite",
    "audit iso 27001",
    "iso 27001",
]

# Offres à exclure même si elles contiennent un mot-clé offensif : ce ne
# sont pas des stages de fin d'études classiques (PFE).
EXCLUDE_CONTRACT_KEYWORDS = [
    "alternance",
    "apprentissage",
    "contrat de professionnalisation",
    "volontariat international",
]

# Durée de stage visée, en mois. Une offre dont la description mentionne
# explicitement une (ou plusieurs) durée(s) toutes en dehors de cette
# fourchette est exclue. Si aucune durée n'est détectée dans le texte,
# l'offre est conservée par défaut (mieux vaut un faux positif qu'un raté).
MIN_DURATION_MONTHS = 5
MAX_DURATION_MONTHS = 6

_DURATION_RE = re.compile(r"(\d{1,2})\s*(?:à\s*\d{1,2}\s*)?mois", re.IGNORECASE)


def extract_duration_months(text):
    """Retourne la liste des durées (en mois) mentionnées dans le texte."""
    if not text:
        return []
    return [int(m) for m in _DURATION_RE.findall(text)]


def is_relevant(title, description=""):
    """Applique le filtre INCLUDE/EXCLUDE + durée sur une offre normalisée."""
    text = f"{title or ''} {description or ''}".lower()

    if not any(kw in text for kw in INCLUDE_KEYWORDS):
        return False

    if any(kw in text for kw in EXCLUDE_CONTRACT_KEYWORDS):
        return False

    durations = extract_duration_months(description)
    if durations and not any(MIN_DURATION_MONTHS <= d <= MAX_DURATION_MONTHS for d in durations):
        return False

    return True
