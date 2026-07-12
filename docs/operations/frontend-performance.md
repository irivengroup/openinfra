# Exploitation du frontend modulaire OpenInfra

## Contrôles locaux

```bash
npm --prefix web ci
npm --prefix web test
npm --prefix web run lint
npm --prefix web run a11y
npm --prefix web run a11y:jsx
npm --prefix web run build
npm --prefix web audit --audit-level=high

PYTHONPATH=src:. python scripts/validate_frontend.py --project-root .
PYTHONPATH=src:. pytest -q --no-cov \
  tests/integration/test_frontend_modular_performance.py \
  tests/integration/test_frontend_runtime_startup.py \
  tests/integration/test_openinfra_web.py
```

Le validateur Vite échoue si le bootstrap dépasse les budgets ou si un chunk métier attendu manque.

## Diagnostic réseau

Au chargement du Dashboard, le navigateur doit demander le shell, le manifeste, les dépendances communes et les endpoints BFF de bootstrap. Il ne doit pas télécharger les fichiers `assets/domains/*.js`, l'index de recherche ni la taxonomie RSOT avant leur utilisation.

Lors de l'ouverture d'un composant, un seul chunk de domaine doit être téléchargé. Les ouvertures suivantes utilisent le cache HTTP immutable et le module déjà chargé. Une recherche globale déclenche une seule fois le chargement de l'index différé.

## Diagnostic du cache de requêtes

Le cache applicatif est en mémoire et disparaît au rechargement de la page. En cas de résultat obsolète :

1. vérifier qu'une mutation appelle l'invalidation du préfixe concerné ;
2. vérifier qu'une nouvelle navigation annule la portée précédente ;
3. contrôler qu'aucune réponse ancienne ne remplace une réponse plus récente ;
4. ne jamais ajouter de persistance navigateur pour contourner le problème.

## Web Vitals

Le runtime émet un événement `openinfra:web-vital` contenant le nom de la métrique, la valeur et l'état du budget. Un collecteur d'observabilité peut écouter cet événement sans modifier le moteur de rendu. Les métriques restent locales tant qu'aucun collecteur explicitement gouverné n'est configuré.

Les budgets sont :

| Mesure | Seuil |
|---|---:|
| LCP p75 | 2 500 ms |
| INP p75 | 200 ms |
| Tâche longue | 200 ms |
| JavaScript initial brut | 250 Kio |
| Shell initial gzip | 150 Kio |

Ces valeurs sont des gates de régression frontend. La qualification de capacité et d'endurance de bout en bout relève d'EPIC-2005.

## Cache HTTP

Les assets versionnés conservent `Cache-Control: public, max-age=31536000, immutable` dans le runtime ASGI. L'index HTML reste revalidé. Une nouvelle version doit modifier le cache-buster ; aucun opérateur ne doit purger manuellement les caches pour un déploiement correctement versionné.

## Rollback

Le rollback applicatif consiste à redéployer les artefacts 0.31.1. Aucune migration de base n'est associée à 0.31.2. Le retour arrière ne requiert donc ni migration inverse ni transformation de données.
