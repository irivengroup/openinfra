# Certification sécurité de release — EPIC-1802

## Décision d'architecture

OpenInfra sépare le contrôle de sécurité continu de la certification de release :

- la CI générale exécute Ruff, mypy, Bandit, tests, CodeQL, `pip-audit` et le scanner de secrets ;
- le workflow de release construit l'artefact final, démarre le runtime réel, scanne le dépôt et l'image, puis exécute une sonde DAST ;
- le service `ReleaseSecurityAuditService` agrège les preuves et refuse un rapport incomplet.

Le moteur est placé dans `openinfra.quality` afin de rester indépendant du domaine métier, des repositories et des interfaces opérateur. Il ne modifie aucune donnée OpenInfra.

## Invariants

- catalogue fermé de huit contrôles obligatoires ;
- commandes exécutées sans shell ;
- délai maximal par contrôle ;
- environnement enfant réduit aux variables nécessaires ;
- sorties nettoyées avant persistance ;
- écritures atomiques des logs et du rapport ;
- empreinte SHA-256 de chaque flux de preuve ;
- digest global déterministe ;
- certification impossible lorsqu'un outil est absent, en timeout, non exécuté ou en échec ;
- mode hors ligne explicitement non certifiant.

## Menaces traitées

- secrets versionnés ou exposés dans les preuves ;
- vulnérabilités Python, Node, système ou image ;
- mauvaises configurations Docker/IaC ;
- régression RBAC ou authentification ;
- routes protégées rendues anonymes ;
- disparition des en-têtes de sécurité web ;
- suppression silencieuse d'un contrôle de release ;
- promotion basée sur une analyse partielle.

## Limites

Le gate ne remplace pas un test d'intrusion humain, un audit de configuration de l'infrastructure cible ni une revue de menace spécifique au déploiement. Il fournit une preuve automatisée bloquante et reproductible pour l'artefact construit.
