# OpenInfra v0.32.12 — rapport de validation

Date : 2026-07-14

## Portée

La version 0.32.12 matérialise **GATE-09 / REL-10 — Promotion Enterprise Scale-out** sans migration PostgreSQL, sans rupture des contrats API/CLI métier et sans modification du thème.

Le gate ne duplique aucun moteur de qualification existant. Il agrège et certifie sept preuves immuables déjà produites par les contrôles spécialisés :

1. contrats P20 de scale-out (`p20-contracts`) ;
2. certification de capacité Enterprise (`enterprise-capacity`) ;
3. campagne de chaos multisite (`multisite-chaos`) ;
4. certification PRA/PCA (`pra-pca`) ;
5. sécurité de release (`release-security`) ;
6. packaging de release signé (`release-packaging`) ;
7. décision GA Go/No-Go (`ga-go-no-go`).

La promotion est refusée si une preuve est absente, périmée, altérée, non certifiée, rattachée à une version incohérente ou, pour la décision GA, à un commit source différent de celui du manifeste GATE-09.

Le périmètre livré ajoute :

- le moteur `openinfra.quality.scaleout_promotion` ;
- la politique machine-readable `enterprise-scaleout-promotion-policy.json` ;
- l'assemblage des sept preuves avec SHA-256 canonique ;
- la certification bloquante `GATE-09 / REL-10` ;
- un workflow GitHub Actions protégé utilisant des run IDs explicites et des artefacts amont immuables ;
- l'intégration au CI, au `quality_gate.py`, au packaging et au smoke du wheel installé ;
- le runbook opérationnel de promotion Enterprise Scale-out.

Le certificat est strictement évaluatif : il ne modifie ni topologie, ni base de données, ni trafic, ni infrastructure.

## Validations exécutées

### Python et architecture

- collecte : **1 267 tests** ;
- suite `tests/unit + tests/performance` : **607/607 PASS** ;
- tests d'intégration transverses ciblés : **59/59 PASS** ;
- couverture ciblée `openinfra.quality.scaleout_promotion` : **274/274 instructions, 100 %** ;
- Ruff format : **370 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **111 modules conformes** ;
- `compileall` : **PASS**.

### Contrats GATE-09 et exploitation

- validation des contrats P20 de scale-out : **PASS** ;
- observabilité globale : **PASS** ;
- observabilité multisite : **PASS** ;
- chaos multisite : **PASS** ;
- PRA/PCA : **PASS** ;
- alignement Enterprise : **PASS** ;
- six profils installateur : **PASS** ;
- frontend runtime validator : **PASS** ;
- documentation GA : **PASS**, version 0.32.12 ;
- support-readiness : **PASS**, version 0.32.12.

Les tests GATE-09 couvrent notamment :

- succès avec exactement sept preuves conformes ;
- preuve manquante, altérée ou périmée ;
- SHA-256 non canonique ;
- path traversal hors racine de preuves ;
- version incohérente ;
- verdict amont non certifié ;
- timestamp absent, futur ou périmé ;
- manifeste trop ancien ou futur ;
- format JSON invalide ;
- commit source GA différent du manifeste ;
- assemblage et copie des sept preuves avec empreintes recalculées.

### Frontend

- tests Node : **63/63 PASS** ;
- contrat statique : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint : **PASS** ;
- build Vite : **PASS** ;
- validation du bundle : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité**.

### Sécurité

- `security_gate.py` : **PASS** ;
- Bandit, périmètre CI `src/openinfra` : **PASS** ;
- `pip-audit --strict --requirement requirements/security-audit.txt --progress-spinner off` : **non exécutable jusqu'au bout dans le sandbox**, échec de résolution DNS vers `pypi.org`.

### Packaging

- build sdist `openinfra-0.32.12.tar.gz` : **PASS** ;
- build wheel `openinfra-0.32.12-py3-none-any.whl` : **PASS** ;
- vérification de contenu des artefacts : **PASS** ;
- présence du moteur, de la politique, du runbook, des scripts et du workflow GATE-09 dans les artefacts attendus : **PASS** ;
- smoke du wheel installé hors de l'arbre source : **PASS** ;
- version installée : **0.32.12** ;
- contrat de promotion installé : **GATE-09 / REL-10**, sept preuves obligatoires ;
- migrations : **54**, dernière `0054_async_outbox_workers.sql`.

## Non-régression visuelle

Les fichiers de thème principal de la version 0.32.12 conservent exactement le même SHA-256 que dans la version 0.32.11 :

```text
334fc797cea05d9c2a0f670d8a098fbc8caa2c55a7cd228f3c296338f52c0555
```

Aucune modification du thème ou de la charte graphique n'a été effectuée.

## Limites de l'environnement courant

La suite complète `tests/architecture + tests/integration` a été tentée par lots. Certains processus d'intégration, notamment autour des installateurs, restent actifs après l'affichage de leurs résultats et ont fait dépasser la fenêtre d'exécution du sandbox. La suite complète n'est donc **pas déclarée intégralement validée localement**, même si les tests transverses directement impactés sont verts.

La couverture globale complète n'a pas été recalculée dans ce sandbox ; le seuil contractuel **>= 98 %** reste bloquant dans GitHub Actions.

Docker et Docker Compose ne sont pas disponibles dans l'environnement courant. Les smokes conteneurisés et les validations réelles de topologie Enterprise restent exécutés par les workflows dédiés sur runners adaptés.

## CDC et roadmap

**Inchangés**. GATE-09 et REL-10 étaient déjà définis dans la roadmap existante ; cette livraison matérialise leur décision de promotion sans introduire de nouvelle exigence fonctionnelle, réglementaire ou architecturale.
