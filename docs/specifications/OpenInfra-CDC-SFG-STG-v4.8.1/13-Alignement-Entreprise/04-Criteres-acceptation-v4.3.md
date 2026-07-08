# Critères d'acceptation v4.3.0

## Editions

- Les trois éditions Lite, Pro et Entreprise sont documentées.
- Les quotas sont vérifiables par tests backend.
- Les feature gates sont centralisés et auditables.
- Les migrations sont communes aux éditions, avec activation fonctionnelle contrôlée.

## Services systemd

- Aucun service systemd ne contient le nom de l'édition.
- Le backend utilise `openinfra.service`.
- Le frontend utilise `openinfra-web.service`.
- Les collecteurs discovery utilisent `openinfra-agent.service`.
- Les workers utilisent `openinfra-worker.service`.

## Frontend

- Le frontend est React + Bootstrap 5.
- Le frontend consomme exclusivement l'API backend.
- Aucune connexion directe à PostgreSQL n'existe depuis le frontend.
- Toute fonctionnalité CLI validée dispose d'une route API et d'un parcours UI correspondant lorsque applicable.

## ITSM externe

- Lite ne peut pas activer les connecteurs ITSM.
- Pro et Entreprise peuvent activer ServiceNow, Jira Service Management, GLPI et Freshservice au minimum.
- Les connecteurs ne créent aucun module ticket interne.
- Les synchronisations sont auditables, rejouables et désactivables.
- Les erreurs de connecteurs n'altèrent pas la RSOT (Ressource Source of Truth).

## Support constructeur

- Un équipement physique ne peut pas être certifié complet sans garantie constructeur et support constructeur.
- Un contrat tiers n'écrase jamais les détails constructeur.
- Les imports et connecteurs génèrent un conflit en cas de divergence.

## Qualité enterprise

- La matrice exigences → tests est complète.
- Le registre de risques est mis à jour.
- Les critères d'acceptation sont testables.
- Le package ZIP est valide.

