# Formulaires Web typés et trust serveur

## Objectif

Le portail OpenInfra ne demande jamais de jeton API à l’utilisateur et n’expose pas la méthode HTTP des opérations métier. Les formulaires présentent uniquement des données fonctionnelles explicites. L’authentification entre `openinfra-web` et `openinfra-api` est établie côté serveur par le proxy Web.

## Modèle de confiance

1. Le navigateur envoie les données métier au proxy same-origin `/api`.
2. `openinfra-web` ignore tout en-tête `Authorization` provenant du navigateur.
3. Le proxy ajoute le bearer configuré côté serveur par `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` ou `--backend-bearer-token-file`.
4. Le backend reçoit `X-OpenInfra-Web-Trust: server-side` et le bearer serveur, jamais un secret fourni par le navigateur.
5. `/config.json`, `/status`, `/bootstrap.json` et `/version` exposent uniquement des métadonnées non sensibles, notamment la version du package et l’état du trust.

## Invariants bloquants

- aucun champ `admin_token`, `authField`, « Token API » ou « Jeton administrateur » dans les catalogues Web ;
- aucun code client générant `Authorization: Bearer …` ;
- aucune méthode HTTP affichée dans les résultats de recherche du portail ;
- présence de champs métier explicites pour les imports asynchrones : fichier, opérateur, format, mapping, clé d’idempotence, taille de lot, intervalle de checkpoint et identifiant de job ;
- version retournée par `/version`, `/config.json` et `/bootstrap.json` identique à la version du package ;
- remplacement d’un éventuel bearer navigateur par le bearer serveur lors du proxy.

## Validation

```bash
python -m pytest -q --no-cov \
  tests/integration/test_contract_web_typed_server_trust.py \
  tests/integration/test_contract_functional_bulk_import.py
node --test web/tests/bulk-import.test.mjs
python scripts/validate_frontend.py --project-root .
```
