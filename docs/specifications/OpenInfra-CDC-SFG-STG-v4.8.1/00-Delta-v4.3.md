# OpenInfra CDC/SFG/STG v4.3.0 — Alignement enterprise, éditions et intégrations ITSM externes

## Objectif

La version 4.3.0 consolide les recommandations précédentes dans un cadre enterprise cohérent, en alignant :

- les exigences fonctionnelles OpenInfra v4 ;
- la stratégie d'éditions OpenInfra Lite, Pro et Entreprise ;
- le packaging et les installateurs ;
- le nommage systemd invariant par édition ;
- les agents de découverte distribués ;
- l'interface web React + Bootstrap 5 ;
- les informations obligatoires de garantie et de support constructeur ;
- l'intégration avec les solutions ITSM externes les plus répandues pour Pro et Entreprise ;
- l'exclusion stricte de toute fonction ITSM intégrée.

## Décisions structurantes

1. OpenInfra reste une solution Ressources Inventory, DCIM, ITAM, Discovery, Dependency Mapping, IPAM, conformité, exploitation et automatisation.
2. OpenInfra ne fournit aucun module natif de ticketing, incident, demande, problème, changement ITIL, catalogue de services ITSM ou SLA ticket.
3. Les éditions Pro et Entreprise doivent pouvoir se connecter aux solutions ITSM externes via connecteurs, API et webhooks.
4. Les noms systemd sont fonctionnels et identiques quelle que soit l'édition.
5. Les collecteurs distribués d'autodiscovery sont des agents et utilisent le suffixe `-agent`.
6. Le backend API utilise le suffixe fonctionnel `-server`.
7. Le frontend est une interface web React + Bootstrap 5 qui consomme exclusivement l'API backend.
8. Toute fonctionnalité exposée en CLI doit être accessible via l'API backend et exploitable depuis le frontend lorsque l'utilisateur possède les droits requis.
9. Les informations constructeur initiales de garantie et de support sont obligatoires pour tout équipement physique et ne peuvent pas être écrasées par un support tiers.
10. Les quotas d'édition sont des garde-fous produit, pas des divergences de modèle de données.

## Manquements corrigés

| Manquement identifié | Correction v4.3.0 |
|---|---|
| Editions définies mais non consolidées dans le référentiel principal | Ajout d'un volume complet `V25-Editions-Packaging-Alignement-Entreprise.md` et matrices dédiées |
| Risque de nommage systemd dépendant de l'édition | Services canoniques invariants : `openinfra.service`, `openinfra.service`, `openinfra-web.service`, `openinfra-agent.service`, `openinfra-worker.service` |
| Ambiguïté proxy/agent | `proxy` n'est pas un rôle produit ; les collecteurs discovery sont des `agents` |
| Frontend non cadré en détail | Frontend React + Bootstrap 5, API-only, aucune connexion DB directe, parité CLI/API/UI |
| Support constructeur pouvant être confondu avec support tiers | Modèle strictement séparé : warranty constructeur, support constructeur initial, contrats tiers |
| Connecteurs ITSM non gouvernés | Cadre d'intégration externe Pro/Entreprise avec mappings, sécurité, webhooks, erreurs et tests |
| Absence de matrice de conformité enterprise | Ajout d'une matrice de pratiques enterprise : sécurité, API, exploitation, data, CI/CD, architecture |
| Risque d'implémentations divergentes par édition | Feature gates déclaratifs, tests multi-éditions et compatibilité ascendante du modèle |

## Non-objectifs confirmés

OpenInfra ne doit pas intégrer :

- gestion native d'incidents ;
- gestion native de demandes ;
- gestion native de problèmes ;
- gestion native de changements ITIL ;
- portail de support utilisateur ;
- files de tickets ;
- SLA de tickets ;
- assignation de tickets ;
- workflow de ticketing.

Les intégrations ITSM servent uniquement à synchroniser des CI, enrichir des tickets externes, créer des liens, pousser des événements et exposer le contexte OpenInfra dans l'outil ITSM externe.

