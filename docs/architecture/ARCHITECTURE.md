## v0.29.76 — Architecture DCIM sites/dépendances et référentiels UI

L’incrément v0.29.76 conserve l’architecture hexagonale OpenInfra : le domaine DCIM porte la règle métier d’étage conditionnel et l’expansion des plages de grille, les services applicatifs orchestrent les contrôles de parents actifs et de cascade non destructive, les ports JSON/PostgreSQL assurent la persistance, puis CLI/API/Web exposent les opérations.

Le référentiel pays ISO est volontairement statique côté domaine pour éviter une dépendance runtime externe. L’API `/api/v1/reference/countries` expose les groupes par continent au portail web, qui rend les champs `country` et `country_code` en sélecteurs.

Les libellés ITAM sont réalignés uniquement dans les interfaces opérateur : `tenant_id` reste le contrat technique compatible, tandis que l’UI présente **Filiale/Subdivision** sous **Organisations**.
