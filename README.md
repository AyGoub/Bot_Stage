# Bot de veille — Stage PFE en cybersécurité

Surveille plusieurs sources d'offres de stage en cybersécurité en France
(offensif, SOC, GRC, purple team...) et notifie sur Discord dès qu'une
offre pertinente apparaît. Le filtre est volontairement large — le tri fin
entre les domaines (pentest vs SOC vs GRC...) se fait manuellement à la
réception des notifications.

## Sources

| Source | Méthode | Statut |
|---|---|---|
| [France Travail](https://francetravail.io) | API officielle (OAuth2) | ✅ Source principale |
| [APEC](https://www.apec.fr) | API JSON interne (reverse-engineering léger) | ✅ Fonctionnelle |
| [LinkedIn](https://www.linkedin.com) | Endpoint public "guest" (HTML) | ✅ Fonctionnelle, avec limites (voir ci-dessous) |
| [Welcome to the Jungle](https://www.welcometothejungle.com) | — | ❌ Non implémentée (voir `sources/wttj.py`) |

**Pourquoi pas Welcome to the Jungle ?** Leur site est protégé par un
challenge anti-bot AWS WAF, et même en le contournant avec un navigateur
headless, la page de recherche a été remplacée par une interface de
"matching" qui n'affiche plus de liste de résultats classique pilotable
par URL. Leur API interne de résultats renvoie 403 même depuis une session
de navigateur légitime. Le détail de l'investigation est documenté dans
`sources/wttj.py`.

**Limite connue de la source LinkedIn** : leur endpoint public ne fournit
que le titre de l'offre (pas la description complète), et leur filtre
"type de poste = stage" ne s'applique pas de façon fiable en accès anonyme.
Le bot compense en n'acceptant que les titres contenant explicitement un
indice de stage ("stage", "stagiaire", "intern", "pfe"...), mais une offre
de pentest en stage dont le titre ne le précise pas explicitement (ex:
juste "Pentester (H/F)") pourrait être manquée.

**Limite (importante) de la source France Travail**, découverte en testant
avec de vraies clés : il n'existe **aucun code "Stage"** dans les
référentiels `typeContrat` (CDI/CDD/MIS/SAI/...) ni `natureContrat` de
l'API — un stage n'étant légalement pas un "contrat de travail" en France,
il est structurellement absent de cette taxonomie. Le paramètre
`typeContrat=STG` documenté dans certains exemples publics n'existe pas et
renvoie une erreur HTTP 400. Comme pour LinkedIn, le bot filtre donc côté
client sur la présence de "stage"/"stagiaire"/"pfe" dans le titre. Testé en
conditions réelles le 2026-07-11 : l'API répond correctement, mais très peu
(voire aucune, au moment du test) offre de stage en cybersécurité
offensive n'y est actuellement publiée — la plupart des offres pentest/red
team sur France Travail sont des CDI. Ce n'est pas un bug, juste la réalité
du marché ; le bot continuera de surveiller.

## Installation locale

```bash
python -m venv .venv
source .venv/bin/activate   # ou .venv\Scripts\activate sous Windows
pip install -r requirements.txt
cp .env.example .env
# éditez .env avec vos identifiants (voir sections ci-dessous)
python main.py
```

Le script charge automatiquement `.env` s'il existe (via `python-dotenv`).
En production (GitHub Actions), les variables viennent des secrets du repo.

## 1. Créer un compte développeur France Travail

Le site a été refondu ; il n'y a plus de menu "Mes applications" séparé,
tout part de la fiche de l'API elle-même :

1. Allez directement sur la page de l'API :
   [francetravail.io/produits-partages/catalogue/offres-emploi](https://francetravail.io/produits-partages/catalogue/offres-emploi)
2. Cliquez sur le bouton **"Utiliser l'API"** en haut de la page.
3. Connectez-vous, ou créez un compte si vous n'en avez pas encore.
4. Le parcours vous propose d'**associer cette API à une application** —
   créez-en une nouvelle à cette étape si vous n'en avez pas.
5. Une fois l'application créée et associée à l'API, récupérez
   l'**Identifiant client** et la **Clé secrète** — ce sont vos
   `FRANCE_TRAVAIL_CLIENT_ID` / `FRANCE_TRAVAIL_CLIENT_SECRET`.

✅ Testé le 2026-07-11 avec de vraies clés : l'authentification OAuth2 et la
recherche fonctionnent. Voir la limite documentée plus haut concernant
l'absence de filtre "Stage" natif dans l'API.

## 2. Créer un webhook Discord

1. Dans Discord, ouvrez les paramètres du salon où vous voulez recevoir les
   notifications → **Intégrations** → **Webhooks** → **Nouveau webhook**.
2. Donnez-lui un nom, choisissez le salon, puis **Copier l'URL du webhook**.
3. C'est votre `DISCORD_WEBHOOK_URL`.

## 3. Configurer les secrets GitHub

Dans votre repo GitHub : **Settings → Secrets and variables → Actions →
New repository secret**, ajoutez :

- `FRANCE_TRAVAIL_CLIENT_ID`
- `FRANCE_TRAVAIL_CLIENT_SECRET`
- `DISCORD_WEBHOOK_URL`

Le workflow `.github/workflows/watch.yml` s'exécute automatiquement toutes
les 30 minutes (et peut être déclenché manuellement depuis l'onglet
**Actions** → **Veille stage cybersécurité offensive** → **Run workflow**).
Il committe et pousse automatiquement `seen_offers.json` s'il a changé, pour
ne jamais renotifier deux fois la même offre.

## 4. Modifier les mots-clés ou cibler une ville précise

Tout se passe dans `config.py`, sans toucher au reste du code :

- `SEARCH_TERMS` : termes envoyés en recherche à chaque source (une requête
  par terme).
- `INCLUDE_KEYWORDS` : une offre n'est retenue que si son texte contient au
  moins un de ces mots-clés (recherche par mot entier, pas sous-chaîne —
  important pour des mots courts comme "soc" ou "grc"). Volontairement
  large par défaut (cybersécurité en général) ; resserrez cette liste si
  vous voulez revenir à un filtre offensif strict (pentest/red team
  uniquement).
- `EXCLUDE_CONTRACT_KEYWORDS` : exclut les offres en alternance/apprentissage
  même si elles matchent un mot-clé de `INCLUDE_KEYWORDS`.
- `MIN_DURATION_MONTHS` / `MAX_DURATION_MONTHS` : fourchette de durée de
  stage acceptée (une offre sans durée précisée est conservée par défaut).
- `FRANCE_TRAVAIL_LOCATION_PARAMS`, `APEC_LOCATION_FILTER`,
  `LINKEDIN_LOCATION` : filtres géographiques optionnels, un par source (les
  formats diffèrent car chaque source a son propre système de codes lieu —
  voir les commentaires dans `config.py`).

## Architecture

```
main.py                  orchestration : appelle chaque source, filtre, déduplique, notifie
config.py                mots-clés de recherche + filtre de pertinence (éditable)
storage.py                lecture/écriture de seen_offers.json (déduplication)
notifier.py               envoi des embeds Discord
sources/
  france_travail.py       API officielle France Travail (OAuth2 + pagination)
  apec.py                 API JSON interne APEC
  linkedin.py              endpoint public "guest" LinkedIn
  wttj.py                  stub documenté (non implémenté)
seen_offers.json          état persistant : { "source:id": "date ISO première détection" }
.github/workflows/watch.yml   cron 30 min + déclenchement manuel, push auto de seen_offers.json
```

Chaque source est appelée dans un `try/except` indépendant dans `main.py` :
si une source échoue (panne, changement de structure, blocage anti-bot),
les autres continuent de fonctionner et l'erreur est loggée clairement.

## Tester une source isolément

```bash
python -c "from sources import apec; print(apec.fetch_offers())"
python -c "from sources import linkedin; print(linkedin.fetch_offers())"
```

(France Travail nécessite vos vraies clés dans l'environnement.)
