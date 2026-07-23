# OpenInfra CDC/SFG/STG v4.5.0 — Service backend canonique

## Objet

La version 4.5.0 corrige et simplifie le modèle systemd du backend. Le déploiement backend installe également PostgreSQL géré par OpenInfra, applique les migrations backend et orchestre le démarrage applicatif. Il n'est donc pas nécessaire de maintenir deux services backend équivalents.

## Décision structurante

- Le service backend canonique unique est `openinfra.service`.
- Le scope d'installation peut rester nommé `server` pour distinguer le backend du frontend et des agents, mais ce scope installe et pilote `openinfra.service`.
- Les migrations backend sont appliquées exclusivement par le scope `server`, avant le démarrage final de `openinfra.service`.
- Le frontend reste porté par `openinfra-web.service`.
- Les collecteurs d'auto discovery restent portés par `openinfra-agent.service`.
- Aucun nom de service systemd ne doit contenir le nom de l'édition.

## Impacts documentaires

- Mise à jour des matrices de services systemd et d'installateurs.
- Mise à jour des exigences packaging et installation autonome.
- Mise à jour des scripts de validation documentaire.
- Ajout du volume V27 dédié à la décision de service backend canonique.
- Ajout des exigences REQ-00571 à REQ-00582.

## Compatibilité

Cette correction ne modifie pas les éditions fonctionnelles. Elle réduit la complexité opérationnelle, évite une duplication de service et clarifie la responsabilité du backend dans les déploiements Pro et Entreprise.
