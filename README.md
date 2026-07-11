# Bot de veille — Stage PFE en cybersécurité offensive

Surveille plusieurs sources d'offres de stage (pentest / red team / sécurité
offensive) en France et notifie sur Discord dès qu'une offre pertinente
apparaît.

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

1. Allez sur [francetravail.io](https://francetravail.io) et créez un compte.
2. Dans votre espace développeur, créez une nouvelle application.
3. Abonnez l'application à l'API **"Offres d'emploi v2"** (scope
   `api_offresdemploiv2`).
4. Récupérez l'**Identifiant client** et la **Clé secrète** — ce sont vos
   `FRANCE_TRAVAIL_CLIENT_ID` / `FRANCE_TRAVAIL_CLIENT_SECRET`.

⚠️ Le code de type de contrat utilisé pour filtrer les stages est `"STG"`
(`sources/france_travail.py`). C'est la valeur documentée par l'API, mais
si aucun résultat ne remonte lors de votre premier test, vérifiez le
référentiel officiel :

```bash
curl -H "Authorization: Bearer VOTRE_TOKEN" \
  "https://api.francetravail.io/partenaire/offresdemploi/v2/referentiel/typesContrats"
```

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
  moins un de ces mots-clés.
- `EXCLUDE_CONTRACT_KEYWORDS` : exclut les offres en alternance/apprentissage
  même si elles matchent un mot-clé offensif.
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
