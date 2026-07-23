---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Contraintes de données

## Contraintes globales

- Toutes les clés étrangères critiques doivent être explicites.
- Toute unicité métier doit être matérialisée par contrainte ou index unique.
- Les contraintes tenant-aware doivent inclure le tenant dans la clé.
- Les objets IPAM doivent empêcher les collisions dans un même espace VRF.
- Les positions DCIM doivent empêcher les collisions rack/U et ligne/colonne incohérentes.
- Les imports doivent valider les contraintes avant application.
- Les violations doivent produire un rapport exploitable et non une erreur silencieuse.

## Contraintes IPAM

- Unicité IP dans `tenant + vrf + address` lorsque la VRF impose l’unicité.
- Prefix contenu dans aggregate si aggregate déclaré.
- IP contenue dans prefix ou range.
- DHCP lease incompatible avec réservation exclusive.
- DNS A/AAAA/PTR corrélables selon règles configurées.
- NAT source/destination typé et audité.

## Contraintes DCIM

- Salle obligatoire pour tout rack.
- Ligne et colonne obligatoires pour tout équipement localisé en salle.
- Coordonnées X/Y/Z validées lorsqu’un plan 2D/3D est activé.
- Position U unique par rack, face et profondeur.
- Poids, énergie et refroidissement ne doivent pas dépasser les seuils autorisés sans dérogation.

## Contraintes audit

- Audit append-only.
- Hash chaîné ou ancrage immuable pour événements critiques.
- Acteur, action, ressource, horodatage, tenant et résultat obligatoires.
