# OpenInfra v0.29.88 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.88`  
Périmètre : `P08 / EPIC-0805 — accessibilité transversale WCAG 2.2 AA et raffinement visuel du header`

## Résultat global

La livraison applique une baseline contractuelle WCAG 2.2 niveau AA à toutes les pages du portail React et du runtime web packagé. Elle ne constitue pas une certification externe : les gates automatisés sont complétés par une checklist de recette manuelle avec technologies d’assistance.

- Tests Python collectés : **639** dans **88 fichiers**.
- Tests unitaires et architecture : **PASS**.
- Tests d’intégration : **PASS**, dont les 57 fichiers exécutés séparément ou en petits groupes.
- Couverture globale exacte : **98,0338384308 %** — `21 091 / 21 514` lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **19 PASS**.
- Lint frontend statique : **PASS**.
- Lint JSX accessible `eslint-plugin-jsx-a11y` : **PASS**.
- Validation du contrat WCAG React/runtime : **PASS**.
- Build frontend Vite **8.1.4** : **PASS**.
- `npm audit --audit-level=high` : **0 vulnérabilité**.

La commande Python instrumentée complète a terminé avec un code retour nul. La couverture a été reconstruite depuis zéro sur l’état final de la release.

## Accessibilité transversale

Garanties validées sur les deux runtimes web :

- liens d’évitement vers le contenu, la navigation des composants et la recherche globale ;
- landmarks sémantiques `banner`, `navigation`, `main`, `form`, `status` et `alert` ;
- navigation des composants par `Tab`, `Maj+Tab`, flèches, `Home`, `End`, `Entrée`, `Espace` et `Échap` ;
- restauration du focus après fermeture des navigations responsive ;
- régions `aria-live` pour changements de navigation, opérations, résultats et états runtime ;
- formulaires avec labels explicites, marqueur textuel obligatoire, `required`, `aria-invalid`, validation native et résultats annoncés ;
- liens externes Swagger/ReDoc annonçant l’ouverture dans un nouvel onglet ;
- focus visible à double contraste ;
- prise en charge de `prefers-contrast: more` et des couleurs forcées ;
- cibles tactiles d’au moins 44 px sur périphériques à pointeur grossier ;
- compensation du header fixe par `scroll-padding-top` et `scroll-margin-top` ;
- suppression des animations lorsque `prefers-reduced-motion: reduce` est actif ;
- absence de média audio/vidéo et d’information communiquée uniquement par le son ;
- contrat imposant sous-titres, transcription et alternative visuelle pour tout futur média sonore.

La procédure de recette manuelle est documentée dans `docs/ui/WEB_ACCESSIBILITY.md` pour NVDA ou JAWS, VoiceOver, TalkBack, navigation clavier seule, zoom 200 % et contraste élevé.

## Header raffiné

- La seconde barre conserve son padding vertical initial de `0,5 rem`.
- La recherche reste haute de `2 rem`, centrée et dimensionnée à 50 % de la largeur utile.
- Les composants restent compacts et alignés à droite sur écran large.
- Les états actif/hover utilisent des fonds translucides et une opacité maîtrisée au lieu d’un contraste suraccentué.
- Le rayon des boutons composants est réduit à `0,22 rem`.
- Les transitions bounce/fade durent moins de 400 ms et sont neutralisées par la préférence de réduction de mouvement.
- Le sélecteur FR/EN et les boutons Swagger/ReDoc utilisent une hauteur de `1,82 rem` sur pointeur précis.
- Sur pointeur grossier, ces contrôles conservent une hauteur minimale de `2,75 rem`.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**, 162 fichiers.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, 57 modules source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- Validation frontend React/runtime packagé : **PASS**.

## CDC, roadmap et installateurs

La livraison réémet le CDC et la roadmap car l’accessibilité transversale et le comportement visuel du header modifient le contrat UX existant.

- CDC v4.8.1 : **PASS** — **825 exigences**, **529 entités**, **625 tests contractuels**.
- Roadmap v2 : **PASS** — **19 phases**, **115 epics**, **8 gates**, **94 validations**.
- `REQ-00789` et `TST-WEB-090` : baseline WCAG 2.2 AA sur toutes les pages.
- `REQ-00825` et `TST-WEB-125` : états translucides, faibles rayons, transitions adaptatives et contrôles réduits.
- `EPIC-0805` : accessibilité et navigation responsive adaptative.
- Six installateurs autonomes Lite/Pro/Enterprise : **PASS**.
- Alignement Enterprise : **PASS**.

## Contrôles limités par l’environnement

- `pip-audit --strict -r requirements/runtime.txt` a été lancé, mais `pypi.org` ne peut pas être résolu. Le contrôle est **non concluant**, et non déclaré comme réussi.
- Docker, Podman et `psql` ne sont pas disponibles ; les smoke tests nécessitant un daemon de conteneurs ou une instance PostgreSQL réelle ne sont pas exécutables localement.
- La capture automatisée Chromium n’est pas disponible dans ce conteneur. Le contrat visuel est validé par tests DOM/CSS, lint, tests Node.js/Python et build Vite, mais pas par comparaison de captures.
- Aucun test automatisé ne remplace une recette humaine complète avec utilisateurs et technologies d’assistance ; la release fournit la checklist correspondante.

## Commandes de reproduction

```bash
ruff format --check src tests scripts docker installers
ruff check src tests scripts docker installers
mypy src/openinfra
bandit -q -r src/openinfra
python scripts/security_gate.py --project-root .
python scripts/quality_gate.py
python scripts/validate_frontend.py --project-root .
python scripts/validate_autonomous_installer.py --root installers
python scripts/validate_enterprise_alignment.py --project-root .
python -m compileall -q src tests scripts docker installers

coverage erase
coverage run -m pytest -q --no-cov tests
coverage report --fail-under=98

npm --prefix web run lint
npm --prefix web run a11y
npm --prefix web run a11y:jsx
npm --prefix web test
npm --prefix web run build
npm --prefix web audit --audit-level=high

python -m build
python scripts/verify_artifact.py dist/openinfra-0.29.88-py3-none-any.whl
python -m venv /tmp/openinfra-wheel-smoke
/tmp/openinfra-wheel-smoke/bin/pip install dist/openinfra-0.29.88-py3-none-any.whl
(cd /tmp && /tmp/openinfra-wheel-smoke/bin/python "$OLDPWD/scripts/smoke_installed_wheel.py")
```
