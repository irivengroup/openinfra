# ADR-0020 — Frontend modulaire et budgets de rendu

## Statut
Accepté — cible roadmap 2.1.0.

## Contexte
La compression réduit le transfert mais ne réduit pas suffisamment le parsing, la compilation et le rendu d’un bundle monolithique.

## Décision
Le portail React est découpé par domaine avec imports dynamiques et chargement à la navigation. Les données serveur sont gérées par un cache de requêtes avec annulation, déduplication, invalidation ciblée et aucune persistance sensible dans `localStorage`. Les listes volumineuses utilisent pagination serveur et virtualisation ; les graphes lourds utilisent agrégation backend et workers navigateur lorsque nécessaire.

## Budgets
- shell initial gzip ou Brotli inférieur ou égal à 150 KiB ;
- JavaScript initial analysé inférieur ou égal à 250 KiB non compressé ;
- aucune requête de catalogue métier hors besoin du module actif ;
- p75 LCP inférieur ou égal à 2,5 s sur profil réseau de référence ;
- INP inférieur ou égal à 200 ms ;
- absence de tâche principale supérieure à 200 ms dans le scénario Dashboard.
