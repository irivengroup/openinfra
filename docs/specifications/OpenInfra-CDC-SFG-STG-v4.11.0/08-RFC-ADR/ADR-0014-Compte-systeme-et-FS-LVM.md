# ADR-0014 — Compte système `openinfra` et filesystem LVM dédié

## Statut

Accepté.

## Contexte

Une installation enterprise doit être reproductible, sécurisée et isoler les données applicatives des chemins système non maîtrisés. L'opérateur ne doit pas créer manuellement l'utilisateur, les permissions et le stockage.

## Décision

Toutes les éditions créent par root un compte système `openinfra` et un filesystem LVM dédié monté sur `/opt/openinfra/`. Les valeurs par défaut sont `rootvg`, `openinfra_lv` et `2GB`.

## Conséquences

- Les installateurs doivent être exécutés par root ou avec privilèges équivalents.
- Les opérations stockage doivent être idempotentes.
- Les règles sudoers doivent être strictes et testées.
- Les services systemd utilisent le compte `openinfra` lorsque applicable.
