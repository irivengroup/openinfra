# Delta contractuel OpenInfra 4.12.0

## Objet

La version 4.12.0 ferme le contrôle de complétude demandé après les évolutions prioritaires de licence offline et de canonicalisation RSOT. Elle n’ajoute aucun comportement métier utilisateur ; elle rend la preuve d’implémentation et la dette résiduelle auditables et bloquantes.

## Ajouts

- `REQ-00861` et `TST-COMP-164`.
- Registre `docs/release/contract-proof-registry-v4.12.csv` couvrant les 667 tests contractuels.
- Classification exacte : 30 preuves automatisées, 589 partielles et 48 externes.
- Résolution de 43 sélecteurs pytest réels.
- Référencement de 74 fichiers de preuve distincts.
- GATE-14 avec six contrôles fail-closed.
- Audit contextuel des marqueurs de complétion, des clés privées, des alias publics retirés et des chemins obsolètes.

## Règle de décision

Une preuve `partial` ou `external` indique un niveau de couverture ou une qualification restant à produire. Elle ne vaut jamais validation fonctionnelle complète. REL-15 est promue localement uniquement si le registre est exhaustif, cohérent et sans entrée manquante ; la promotion production reste bloquée par les preuves externes non exécutées sur infrastructure cible.
