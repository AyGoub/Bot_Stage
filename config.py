"""
Configuration éditable du bot de veille stages cybersécurité.

Le filtre couvre la cybersécurité au sens large (offensif, SOC, GRC, purple
team...) : le tri fin entre ces domaines se fait manuellement par vous à la
réception des notifications Discord. Modifiez ce fichier pour ajuster le
ciblage (mots-clés, ville/région, durée de stage visée) sans toucher au
reste du code.
"""
import re

# ---------------------------------------------------------------------------
# Termes de recherche envoyés à chaque source. Une requête est faite par
# terme et par source ; les résultats sont fusionnés puis dédupliqués avant
# d'être passés au filtre de pertinence ci-dessous.
# ---------------------------------------------------------------------------
SEARCH_TERMS = [
    "cybersécurité",
    "cybersecurity",
    "sécurité informatique",
    "sécurité des systèmes d'information",
    "pentest",
    "red team",
    "purple team",
    "SOC",
    "GRC",
    "test intrusion",
    "sécurité offensive",
    "ethical hacking",
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
# termes (recherche insensible à la casse, sous-chaîne simple). Volontairement
# large : cybersécurité en général (offensif, SOC, GRC, purple team...), le
# tri fin se fait manuellement à la réception des notifications Discord.
INCLUDE_KEYWORDS = [
    "cybersécurité",
    "cybersecurite",
    "cybersecurity",
    "cyber sécurité",
    "sécurité informatique",
    "sécurité des systèmes d'information",
    "sécurité si",
    "ssi",
    "sécurité réseau",
    "sécurité des données",
    "pentest",
    "pentester",
    "pénétration",
    "penetration",
    "red team",
    "redteam",
    "purple team",
    "blue team",
    "offensive",
    "ethical hacking",
    "intrusion",
    "exploitation de vulnérabilités",
    "exploitation de vulnerabilites",
    # "vulnérabilité" seul est volontairement absent : trop ambigu hors
    # contexte IT (vulnérabilité sismique/structurelle d'un bâtiment,
    # vulnérabilité sociale...). D'où ces variantes composées à la place.
    "vulnérabilité informatique",
    "vulnérabilité applicative",
    "vulnérabilités de sécurité",
    "soc",
    "grc",
    "conformité",
    "conformite",
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

_keyword_pattern_cache = {}


def _keyword_pattern(keywords):
    """Compile (et met en cache) un regex à limites de mots pour une liste
    de mots-clés. Nécessaire pour des mots courts et ambigus comme "soc" ou
    "ssi", qui en simple sous-chaîne matcheraient "société", "association",
    etc. — ce qui viderait le filtre de tout son sens sur des offres FR."""
    key = tuple(keywords)
    if key not in _keyword_pattern_cache:
        pattern = "|".join(r"\b" + re.escape(kw) + r"\b" for kw in keywords)
        _keyword_pattern_cache[key] = re.compile(pattern, re.IGNORECASE)
    return _keyword_pattern_cache[key]


def _contains_any_keyword(text, keywords):
    return bool(_keyword_pattern(keywords).search(text))


def extract_duration_months(text):
    """Retourne la liste des durées (en mois) mentionnées dans le texte."""
    if not text:
        return []
    return [int(m) for m in _DURATION_RE.findall(text)]


def is_relevant(title, description=""):
    """Applique le filtre INCLUDE/EXCLUDE + durée sur une offre normalisée."""
    text = f"{title or ''} {description or ''}"

    if not _contains_any_keyword(text, INCLUDE_KEYWORDS):
        return False

    if _contains_any_keyword(text, EXCLUDE_CONTRACT_KEYWORDS):
        return False

    durations = extract_duration_months(description)
    if durations and not any(MIN_DURATION_MONTHS <= d <= MAX_DURATION_MONTHS for d in durations):
        return False

    return True
