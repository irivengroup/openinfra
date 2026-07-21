# OpenInfra CDC/SFG/STG v4.5.0 — Service backend canonique, installation autonome cluster et bootstrap dépendances

## Objet

La version 4.4.0 ajoute une exigence structurante d'installation autonome pour les déploiements cluster backend, frontend, PostgreSQL et agents d'auto discovery.

L'objectif est que l'opérateur ne soit pas expert PostgreSQL HA, système, réseau applicatif, frontend ou clustering. Il fournit uniquement les informations réseau nécessaires : FQDN, IP, masque, VIP, passerelle et DNS. L'installateur détecte l'OS, installe les dépendances, configure les services, applique les migrations backend, valide l'état final et produit un rapport de preuve.

## Décisions ajoutées

- Les installateurs sont dans un dossier racine `installers/`, séparé de `src/`.
- Aucun installateur ne doit être placé dans `src/`.
- Le backend utilise le service canonique unique `openinfra.service`; le scope d'installation peut rester `server`, mais il ne crée pas de service systemd backend distinct.
- Les collecteurs d'auto discovery utilisent le suffixe fonctionnel `-agent` et le service canonique `openinfra-agent.service`.
- Le frontend utilise le service canonique `openinfra-web.service`.
- Le frontend React + Bootstrap 5 consomme exclusivement l'API backend.
- Le backend installer déploie toutes les migrations applicatives et base de données avant le démarrage applicatif final.
- Les migrations sont idempotentes, versionnées, vérifiées et protégées par verrou applicatif.
- Les dépendances système, runtime, PostgreSQL, HA, réseau, certificats, observabilité et sécurité sont installées automatiquement selon l'édition et le scope.
- Le mode cluster configure en autonomie backend canonique, frontend, agents, VIP, load balancing, health checks, services systemd et validation finale.

## Périmètre documentaire ajouté

- Volume V26 : installation autonome, cluster bootstrap, dépendances et migrations.
- Documents techniques d'installation autonome.
- ADR-0011 et ADR-0012.
- Matrices installateurs, dépendances, migrations et ports.
- Exigences REQ-00509 à REQ-00570.
- Tests TST-V44-001 à TST-V44-050.
- Cas d'usage UC-V44-0001 à UC-V44-0008.
- Risques RISK-0041 à RISK-0048.

## Compatibilité

Cette version ne modifie pas le périmètre fonctionnel des éditions. Elle renforce uniquement la capacité d'installation, d'exploitation et de validation.

L'exclusion de l'ITSM intégré reste inchangée. Les éditions Pro et Entreprise conservent uniquement les connecteurs ITSM externes.
