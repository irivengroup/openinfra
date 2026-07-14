# OpenInfra v0.32.11 — rapport de validation

Date : 2026-07-14

## Portée

La version 0.32.11 réalise **P17 / EPIC-1706 — Chaos multisite** sans migration PostgreSQL, sans rupture API/CLI métier et sans modification du thème.

Le périmètre livré ajoute :

- un profil versionné `openinfra-multisite-chaos-v1` ;
- six scénarios obligatoires : réseau, site, agent, base de données, saturation de file et frontend ;
- un runner de campagne utilisant un harness externe à protocole fixe et sans shell arbitraire ;
- mesure disponibilité, taux d’erreur, récupération et intégrité SHA-256 avant/après ;
- récupération systématique et arrêt de campagne après récupération/rollback non vérifié ;
- assemblage de six preuves et digest canonique du manifeste ;
- certification bloquante de la dégradation contrôlée et de l’absence de corruption ;
- workflow GitHub Actions protégé, runbook, tests, CI, quality gate et packaging alignés.

## Validations exécutées

### Python et architecture

- collecte : **1 255 tests** ;
- suite `tests/unit + tests/performance` : **600/600 PASS** ;
- tests EPIC-1706 ciblés : **11/11 PASS** ;
- tests d’intégration transverses ciblés : **40/40 PASS** ;
- couverture ciblée `openinfra.quality.multisite_chaos` : **201/201 instructions, 100 %** ;
- Ruff format : **365 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **110 modules conformes** ;
- `compileall` : **PASS**.

### Contrats d’exploitation

- observabilité globale : **PASS** ;
- observabilité multisite : **PASS** ;
- PRA/PCA : **PASS** ;
- chaos multisite : **PASS**, six scénarios ;
- alignement Enterprise : **PASS** ;
- six profils installateur : **PASS** ;
- frontend runtime validator : **PASS** ;
- documentation GA : **PASS**, version 0.32.11 ;
- support-readiness : **PASS**, version 0.32.11.

### Frontend

- tests Node : **63/63 PASS** ;
- contrat statique : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint : **PASS** ;
- build Vite : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité**.

### Sécurité

- `security_gate.py` : **PASS** ;
- Bandit, périmètre CI `src/openinfra` : **PASS** ;
- `pip-audit --strict` : **non exécutable jusqu’au bout dans le sandbox**, échec de résolution DNS vers `pypi.org`.

### Packaging

- build sdist `openinfra-0.32.11.tar.gz` : **PASS** ;
- build wheel `openinfra-0.32.11-py3-none-any.whl` : **PASS** ;
- vérification de contenu des artefacts : **PASS** ;
- présence du profil, du runbook, du workflow et des scripts EPIC-1706 dans le sdist : **PASS** ;
- smoke du wheel installé : **PASS** ;
- version installée : **0.32.11** ;
- contrat `multisite_chaos_certification` : **PASS** ;
- migrations : **54**, dernière `0054_async_outbox_workers.sql`.

Le premier essai du smoke dans un venv sans dépendances runtime a échoué sur `uvicorn` absent. Le smoke final a été exécuté avec le wheel installé dans un répertoire isolé du code source et les dépendances runtime disponibles dans l’environnement, ce qui valide bien le contenu du wheel sans importer l’arbre `src` local.

## Non-régression visuelle

Le fichier `src/openinfra/interfaces/rendering/static/assets/openinfra-web.css` conserve exactement le même SHA-256 que dans la livraison 0.32.10 :

```text
334fc797cea05d9c2a0f670d8a098fbc8caa2c55a7cd228f3c296338f52c0555
```

Aucune modification du thème ou de la charte graphique n’a été effectuée.

## Limites de l’environnement courant

La suite complète `tests/architecture + tests/integration` a dépassé la fenêtre d’exécution du sandbox après plusieurs tests réussis et sans échec observé avant le timeout. Elle n’est donc **pas déclarée intégralement validée localement**.

La couverture globale complète n’a pas été recalculée dans ce sandbox ; le seuil contractuel **>= 98 %** reste bloquant dans GitHub Actions.

Docker et Docker Compose ne sont pas disponibles dans l’environnement courant. Les smokes conteneurisés et la campagne de chaos réelle sur topologie Enterprise représentative restent donc exécutés par les workflows dédiés sur runners self-hosted.

## CDC et roadmap

**Inchangés**. EPIC-1706 était déjà défini dans la roadmap existante et cette livraison n’introduit aucune nouvelle exigence fonctionnelle, réglementaire ou architecturale nécessitant leur révision.
