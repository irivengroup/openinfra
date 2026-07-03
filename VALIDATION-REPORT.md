# OpenInfra Python POO v0.20.0 — Rapport de validation

Date : 2026-07-03

## Synthèse

- Version livrée : OpenInfra Python POO v0.20.0
- Roadmap : P05 / EPIC-0503 — VLAN/VXLAN/ASN/BGP fondation
- Baseline : OpenInfra Python POO v0.19.0
- Runtime production : serveur Linux natif, virtualenv Python, systemd, PostgreSQL
- Docker : environnement facultatif de lab/smoke uniquement, non requis en production
- Seuil officiel de couverture : >= 98 %
- Couverture obtenue : 98.08 %
- Résultat global : conforme

## Fonctionnalités livrées

- Domaine IPAM réseau : `VlanGroup`, `Vlan`, `VxlanVni`, `AutonomousSystem`, `BgpPeer`, `NetworkIdentifierPolicy`.
- Services applicatifs : définition des groupes VLAN, VNI/VXLAN, VLAN, ASN, pairs BGP et rapport d’attachements réseau.
- Règles métier :
  - VLAN ID borné à 1..4094 ;
  - VNI borné à 1..16777215 ;
  - ASN borné à 1..4294967295 ;
  - route targets normalisées au format `ASN:NUMBER` ;
  - VNI unique par tenant ;
  - VLAN attaché à un VNI obligatoirement dans le même VRF ;
  - ASN local et distant distincts pour un pair BGP ;
  - pair BGP IPv4/IPv6 cohérent avec l’adresse du voisin.
- Backends : JSON atomique et PostgreSQL alignés sur les ports applicatifs.
- Migration PostgreSQL : `0017_ipam_networking_foundation.sql` partitionnée par `tenant_id`.
- CLI : `define-vlan-group`, `define-vxlan-vni`, `define-vlan`, `define-asn`, `define-bgp-peer`, `network-bindings`.
- API HTTP : endpoints IPAM réseau ajoutés dans OpenAPI.
- CI GitHub Actions : rendu migration `0017` et smoke IPAM réseau ajoutés ; sécurité bloquante conservée.
- Documentation : README, architecture, runbooks, OpenAPI, changelog et traçabilité mis à jour.

## Validations exécutées

| Validation | Résultat |
| --- | --- |
| `python3 -m ruff format --check src tests scripts docker` | Réussi |
| `python3 -m ruff check src tests scripts docker` | Réussi |
| `python3 -m mypy src/openinfra` | Réussi |
| `python3 -m bandit -q -r src/openinfra` | Réussi |
| `PYTHONPATH=src python3 scripts/security_gate.py --project-root .` | Réussi |
| `python3 -m pip_audit --strict --requirement requirements/security-audit.txt --progress-spinner off --dry-run` | Réussi |
| `PYTHONPATH=src python3 -m pytest -q` | 189 tests réussis |
| Couverture globale | 98.08 % |
| `PYTHONPATH=src python3 scripts/quality_gate.py` | Réussi |
| `PYTHONPATH=src python3 -m compileall -q src tests scripts docker` | Réussi |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli version` | 0.20.0 |
| `PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4` | Réussi |
| Rendu migrations PostgreSQL 0001 à 0017 | Réussi |
| Rendu migration `0017_ipam_networking_foundation` | Réussi |
| Smoke CLI IPAM VLAN/VXLAN/ASN/BGP JSON | Réussi |
| `python3 scripts/native_runtime_smoke.py` | Réussi |
| Validation YAML GitHub Actions / OpenAPI | Réussi |
| `python3 -m build` | Réussi |
| `python3 scripts/verify_artifact.py dist/*.whl` | Réussi |

## Contrôles non exécutés localement

- Matrice GitHub Actions complète Python 3.11, 3.12, 3.13 et 3.14 : seul Python 3.13.5 était disponible localement.
- CodeQL et Dependency Review : exécutables côté GitHub Actions uniquement.
- Audit `pip-audit` réseau complet : non exécuté localement ; la configuration d’audit par fichier `requirements/security-audit.txt` est validée en `--dry-run` et intégrée à la CI.
- Docker Compose réel : non exécuté, Docker n’est pas requis en production.
- PostgreSQL réel : non exécuté, aucun serveur PostgreSQL local disponible.

## Risques résiduels

- La validation PostgreSQL réelle doit être exécutée dans l’environnement d’intégration disposant d’un cluster PostgreSQL.
- La matrice Python 3.14 dépend de la disponibilité de Python 3.14 dans GitHub Actions.
- Les scans CodeQL/Dependency Review doivent être confirmés côté GitHub après push.
