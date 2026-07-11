# Performance de chargement du portail web

OpenInfra `0.29.105` corrige les lenteurs de chargement du runtime web packagé sans modifier les contrats API, les formulaires ni les règles d’accès.

## Causes corrigées

La version précédente cumulait trois coûts : environ 600 Ko de CSS/JavaScript servis sans compression, une directive `no-store` appliquée aux assets statiques, puis le chargement systématique de cinq catalogues métier au démarrage du Dashboard. La sonde de disponibilité backend faisait également partie du bootstrap attendu.

## Transport statique

Les ressources sous `/assets/` sont servies avec :

- gzip pour les contenus texte supérieurs ou égaux à 1 024 octets ;
- un ETag distinct pour les représentations identité et gzip ;
- `Vary: Accept-Encoding` ;
- `304 Not Modified` lorsque `If-None-Match` correspond ;
- `Cache-Control: public, max-age=31536000, immutable` pour les URL portant `?v=<version>` ;
- une revalidation bornée à une heure pour les accès directs non versionnés ;
- `no-cache` pour `index.html` afin qu’une nouvelle version référence toujours ses nouveaux assets.

Les réponses de configuration, statut, readiness et proxy API restent en `no-store`.

## Bootstrap non bloquant

`/bootstrap.json` agrège la configuration publique du BFF, sa version et l’état des formulaires protégés. Le runtime effectue ensuite `/ready` en parallèle ; une indisponibilité backend met à jour l’indicateur d’état mais ne retarde pas l’affichage du Dashboard.

## Catalogues chargés à la demande

Aucun catalogue métier n’est chargé sur la page d’accueil. Lorsqu’un opérateur sélectionne une opération, le runtime détermine les dépendances à partir des champs du formulaire :

- `country-select` : référentiel des pays ;
- `organization-select` et `tenant-select` : organisations et filiales en parallèle ;
- `partner-select` : partenaires après résolution du périmètre organisationnel ;
- références DCIM : topologie du tenant sélectionné.

Les requêtes simultanées identiques sont dédupliquées. Un changement d’opération invalide proprement le rendu attendu afin qu’une réponse tardive ne remplace pas le formulaire actif.

## Budgets bloquants

Les tests imposent :

- moins de 55 Ko gzip pour `openinfra-web.js` ;
- moins de 125 Ko gzip pour les cinq assets CSS/JavaScript du runtime ;
- un ratio gzip global inférieur à 22 % ;
- la présence d’URL versionnées pour les CSS, le module principal et ses dépendances ;
- l’absence de chargement des catalogues dans `refreshRuntime()`.

## Validation locale

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/integration/test_openinfra_web.py \
  tests/integration/test_frontend_runtime_startup.py

npm --prefix web test
python scripts/validate_frontend.py --project-root .
```

Pour contrôler les en-têtes depuis un poste client :

```bash
curl -I -H 'Accept-Encoding: gzip' \
  'http://127.0.0.1:2006/assets/openinfra-web.js?v=0.29.105'
```

La réponse doit contenir `Content-Encoding: gzip`, `Vary: Accept-Encoding`, un `ETag` et la politique `immutable`.
