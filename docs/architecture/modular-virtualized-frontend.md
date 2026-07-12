# Frontend modulaire et virtualisé — EPIC-2004

## Objectif

OpenInfra 0.31.2 découpe le portail web par domaine afin que le Dashboard ne charge ni les 274 opérations métier, ni l'index de recherche complet, ni la taxonomie RSOT au démarrage. Le shell initial reste autonome, accessible et compatible avec le BFF existant.

## Architecture

Le portail packagé sépare huit domaines métier :

- RSOT ;
- IPAM ;
- DCIM ;
- ITAM ;
- Discovery ;
- Imports/Exports ;
- Intégrations externes ;
- Sécurité/RBAC/Audit.

`openinfra-domain-manifest.js` ne contient que les métadonnées nécessaires au Dashboard et les chargeurs dynamiques. Chaque fichier `assets/domains/<domaine>.js` est importé au premier accès au domaine. L'index `openinfra-search-index.js` est chargé uniquement à la première recherche globale. La taxonomie RSOT est livrée avec le chunk RSOT.

Le portail React de référence utilise le même découpage avec les imports dynamiques Vite. Le bootstrap `web/src/bootstrap.js` reste le seul point d'entrée initial ; Vite produit un chunk par domaine, un chunk de recherche différé et un chunk séparé pour la taxonomie RSOT.

## Cache et concurrence

`OpenInfraQueryCache` fournit :

- déduplication des lectures concurrentes par clé ;
- TTL et éviction LRU bornée ;
- annulation par portée avec `AbortController` ;
- invalidation ciblée après mutation ;
- génération monotone empêchant une réponse obsolète de repeupler le cache ;
- stockage exclusivement en mémoire, sans `localStorage`, `sessionStorage` ni IndexedDB.

Les réponses sensibles ne persistent donc pas dans le navigateur. Une mutation invalide uniquement les clés concernées ; les requêtes non liées conservent leur cache.

## Virtualisation

Les groupes de résultats dépassant 40 éléments sont virtualisés. La fenêtre rend uniquement les lignes visibles avec surbalayage, tout en conservant la hauteur totale de défilement et les attributs accessibles. Le portail React utilise `VirtualizedList`; le runtime packagé utilise `OpenInfraVirtualList`.

## Web Vitals et budgets

Le runtime observe en mémoire :

- LCP (Largest Contentful Paint), budget 2 500 ms ;
- INP (Interaction to Next Paint), budget 200 ms ;
- tâches longues, budget 200 ms.

Les métriques sont bornées, non persistantes et diffusées par l'événement `openinfra:web-vital`. Elles servent au diagnostic et à l'observabilité ; la certification de capacité réelle demeure dans EPIC-2005.

Les gates de build imposent :

- JavaScript initial brut inférieur ou égal à 250 Kio ;
- shell initial compressé inférieur ou égal à 150 Kio ;
- présence des chunks métier, recherche et taxonomie ;
- absence des définitions métier dans le shell initial.

## Compatibilité et sécurité

Les routes, payloads, permissions, libellés et identifiants d'opération restent inchangés. Le découpage ne modifie pas les contrats API/CLI. Les erreurs de chargement sont rendues dans le shell accessible existant. Les imports sont statiques et fermés par manifeste ; aucune URL de module fournie par l'utilisateur n'est exécutée.

Aucune feuille de style n'a été modifiée pour cette évolution.
