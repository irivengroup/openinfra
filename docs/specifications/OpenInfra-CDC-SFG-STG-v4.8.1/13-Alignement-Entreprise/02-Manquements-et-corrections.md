# Manquements éventuels identifiés et corrections apportées

| Domaine | Manquement possible | Correction apportée |
|---|---|---|
| Editions | Risque de modèles divergents par édition | Même modèle de données, feature gates et quotas par édition |
| Packaging | Risque de services spécifiques par édition | Noms systemd invariants et suffixes fonctionnels |
| Discovery | Terme proxy ambigu | Remplacement par agent collecteur `openinfra-agent.service` |
| Frontend | Parité CLI/API/UI non explicite | Obligation de parité fonctionnelle via API backend |
| ITSM | Risque d'introduire un ticketing interne | Interdiction explicite ; connecteurs externes uniquement Pro/Entreprise |
| Support | Support tiers pouvant écraser constructeur | Entités séparées et conflit obligatoire en cas de divergence |
| Sécurité | Connecteurs externes trop permissifs | OAuth/mTLS/tokens, Vault, RBAC, audit, rate limit, retry contrôlé |
| Résilience | Connecteurs bloquants | Queue asynchrone, DLQ, dry-run, replay, désactivation sans impact RSOT |
| API | Risque d'exports synchrones | Exports massifs asynchrones uniquement |
| Performance | Risque de scans complets | Partitionnement, index, filtres sélectifs, tests EXPLAIN |
| Gouvernance | Sources concurrentes non priorisées | Source autoritative par attribut et score de confiance |
| Données constructeur | Découverte ou import destructif | Import/discovery non destructifs pour données constructeur |
| Licences | Contournement quotas côté UI | Application des quotas côté backend uniquement |
| Observabilité | Manque de visibilité connecteurs | Métriques lag, erreurs, retries, DLQ, taux sync, latence API cible |

