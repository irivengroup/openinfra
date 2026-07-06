---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 4.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Note de cadrage CCTP / CdCF

## 1. Objet du marché

Le présent dossier définit les spécifications fonctionnelles générales, les spécifications techniques générales, les contraintes d’architecture, les exigences de sécurité, les performances attendues, les critères d’acceptation et les livrables de la solution OpenInfra.

OpenInfra doit être une plateforme open source de référence d’infrastructure, couvrant IT Ressources Management, DCIM, ITAM, Discovery, Dependency Mapping et IPAM Enterprise++, sans fonction ITSM intégrée.

## 2. Portée contractuelle

L’intégrateur ou l’équipe de développement devra fournir une solution complète incluant :

- code applicatif ;
- schéma PostgreSQL versionné ;
- migrations ;
- API REST et GraphQL ;
- interface utilisateur ;
- collectors de découverte ;
- workers asynchrones ;
- charts Kubernetes ;
- packaging conteneur ;
- observabilité ;
- tests automatisés ;
- documentation d’exploitation ;
- runbooks PRA/PCA ;
- documentation développeur ;
- procédures de sécurité ;
- démonstration des critères d’acceptation.

## 3. Exclusions contractuelles

OpenInfra ne doit pas intégrer de module natif de ticketing, incident, demande ou change management ITSM. Les interactions avec ITSM doivent être réalisées par connecteurs, webhooks, API ou plugins.

## 4. Exigences impératives

Les exigences classées N1 sont impératives. Une offre ne couvrant pas une exigence N1 doit être considérée non conforme, sauf dérogation formelle validée par l’architecture d’enterprise.

## 5. Preuves attendues

Chaque exigence N1 doit être démontrée par au moins une preuve : test automatisé, test de charge, démonstration fonctionnelle, revue de code, inspection de schéma, rapport de sécurité, rapport d’exploitation ou rapport d’architecture.

## 6. Réception

La réception ne peut être prononcée que si :

- les matrices d’exigences sont complètes ;
- les tests associés passent ;
- les performances sont mesurées ;
- les scénarios de bascule et restauration sont démontrés ;
- les APIs sont documentées ;
- les migrations sont rejouables ;
- les critères de sécurité sont validés ;
- les risques résiduels sont acceptés formellement.


## Addendum CCTP/CdCF v4

La présente version ajoute des capacités fonctionnelles de gouvernance, qualité, flux, certificats, conformité réseau, FinOps, opérations terrain, simulation, GreenOps, SBOM, Kubernetes avancé et policy engine. Ces ajouts sont contractuels et vérifiables via les matrices `Exigences.csv`, `Traceabilite.csv`, `Tests.csv`, `Cas-usage.csv`, `Registre-risques.csv` et `Matrice-de-conformite.csv`.

L’exclusion ITSM demeure inchangée : OpenInfra peut s’intégrer à un ITSM externe, mais ne fournit pas de tickets, incidents, demandes ou changements natifs.


## Exigences complémentaires v4.6

Les éditions Pro et Entreprise doivent pouvoir s'intégrer à LDAP/IPA pour l'authentification des utilisateurs humains et la gestion des groupes RBAC. Cette intégration ne transforme pas OpenInfra en solution IAM : l'annuaire fournit l'identité et les groupes, OpenInfra conserve la décision d'autorisation applicative.

Les scopes applicatifs `lite/all-in-one`, `pro/server`, `pro/web`, `enterprise/server`, `enterprise/web` et `enterprise/agent` doivent créer lors de l'installation un compte système `openinfra` et un filesystem LVM dédié monté sur `/opt/openinfra/`. Les valeurs par défaut internes sont `rootvg`, `openinfra_lv` et `2GB`. Le scope `enterprise/agent` reste exclu uniquement de PostgreSQL, PGDATA, du symlink data et des migrations backend.
