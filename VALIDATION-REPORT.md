# OpenInfra v0.29.89 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.89`  
Périmètre : `P15 / EPIC-1502 — Matrice de flux déclarés et observés`

## Résultat global

La livraison implémente une matrice de conformité réseau gouvernée, sans déploiement automatique de règles et sans duplication du RSOT. Les déclarations sont révisables et historisées ; les observations sont immuables et idempotentes ; la comparaison est déterministe, tenant-aware, bornée et auditée.

- Tests Python collectés : **676** dans **91 fichiers**.
- Tests unitaires : **263 PASS** dans 31 fichiers.
- Tests d’intégration : **410 PASS** dans 59 fichiers.
- Tests d’architecture : **3 PASS**.
- Couverture globale exacte : **98,0075943712 %** — `21 939 / 22 385` lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **19 PASS**.
- Lint frontend, accessibilité JSX, contrat WCAG et build Vite : **PASS**.
- `npm audit --audit-level=high` : **0 vulnérabilité**.

La suite Python a été exécutée par groupes indépendants afin d’éviter le timeout du runner monolithique. Les 91 fichiers ont contribué à la couverture consolidée. Les fichiers modifiés pour relever la couverture ont ensuite été rejoués explicitement sans échec.

## Matrice de flux

Garanties validées :

- déclarations `allow`/`deny` avec code stable, priorité, propriétaire, justification et validité ;
- sélecteurs `any`, `object:<clé RSOT>` et `cidr:<réseau>` ;
- protocoles `any`, TCP, UDP, SCTP, ICMP, ICMPv6, ESP, AH et GRE ;
- validation stricte des plages de ports ;
- observations NetFlow, sFlow, IPFIX, pare-feu, application, import ou manuel ;
- idempotence tenant/clé et détection d’une charge contradictoire par empreinte SHA-256 ;
- classification `compliant`, `denied-observed`, `undeclared-observed` et `declared-unobserved` ;
- sélection déterministe des déclarations par priorité et spécificité ;
- fenêtre maximale de 31 jours ;
- limites de 5 000 déclarations et 10 000 observations par comparaison ;
- pagination et détection des curseurs cycliques/non progressifs ;
- permissions `flow.read` et `flow.write`, rôles `flow:reader` et `flow:operator` ;
- isolation stricte par tenant et événements d’audit ;
- persistance JSON et PostgreSQL ;
- migration PostgreSQL `0041_flow_matrix.sql`, partitionnée en 16 partitions par table et indexée ;
- six commandes CLI, six routes HTTP/OpenAPI et six opérations web FR/EN.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**, 167 fichiers.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, 59 modules source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- Validation frontend React/runtime packagé : **PASS**.

Les suppressions Bandit `B608` concernent uniquement des listes de colonnes et prédicats SQL constants. Toutes les valeurs opérateur restent transmises par paramètres PostgreSQL ; aucun contenu utilisateur n’est interpolé dans la requête.

## Frontend

- `npm ci --prefix web --ignore-scripts --no-audit --no-fund` : **PASS**.
- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run a11y` : **PASS**.
- `npm --prefix web run a11y:jsx` : **PASS**.
- `npm --prefix web test` : **19 PASS**.
- `npm --prefix web run build` : **PASS**, Vite 8.1.4.
- `npm --prefix web audit --audit-level=high` : **0 vulnérabilité**.
- Parité byte-identique du moteur i18n React/runtime : **PASS**.

## CDC, roadmap et installateurs

Aucune nouvelle recommandation ne modifie l’existant : EPIC-1502 était déjà défini dans la roadmap. Le CDC et la roadmap ne sont donc ni modifiés ni réémis.

- Comparaison byte-for-byte avec la v0.29.88 : **PASS**, 241 fichiers contractuels.
- Empreinte agrégée inchangée : `4af183c96e88196b6aa44f5ecd5a57ffc768c1c9cb54bbf0d8752af60e34a90c`.
- CDC v4.8.1 : **PASS** — 825 exigences et 625 tests contractuels.
- Roadmap v2 : **PASS** — 19 phases, 115 epics, 8 gates et 94 validations.
- Six installateurs autonomes Lite/Pro/Enterprise : **PASS**.
- Alignement Enterprise : **PASS**.

## Packaging et smoke tests

- Wheel : `openinfra-0.29.89-py3-none-any.whl` — **PASS**.
- Sdist : `openinfra-0.29.89.tar.gz` — **PASS**.
- Vérification d’artefact : **PASS**.
- Installation du wheel dans un environnement virtuel vierge : **PASS**.
- Dépendance runtime `defusedxml` résolue depuis les métadonnées du wheel : **PASS**.
- Version installée : `0.29.89`.
- Trois points d’entrée console : **PASS**.
- OpenAPI packagé : **PASS**.
- Trois routes Graphe et six routes Matrice de flux : **PASS**.
- Trois assets web runtime : **PASS**.
- Migrations packagées : **41**, dernière migration `0041_flow_matrix.sql`.
- Sdist sans cache, `node_modules`, `web/dist` ni fichier de couverture : **PASS**.

## Contrôles limités par l’environnement

- `pip-audit --strict --requirement requirements/runtime.txt` a été lancé mais reste **non concluant** : le runner ne peut pas résoudre `pypi.org`.
- Aucun daemon Docker ou Podman n’est disponible.
- Aucun serveur PostgreSQL live n’est disponible ; les migrations, adaptateurs, conversions, contraintes, index et politiques SQL sont validés statiquement et par tests simulés.
- La recette Chromium visuelle n’est pas disponible dans ce conteneur.
