# Guide utilisateur

Version cible : `0.34.20`

## Navigation

L’interface web est disponible par défaut sur `http://127.0.0.1:2006`. Le Dashboard présente les indicateurs synthétiques. La barre supérieure donne accès aux composants et la sidebar regroupe les opérations par contexte métier.

Les composants principaux sont :

- RSOT : référentiel des ressources et dépendances ;
- DCIM : sites, bâtiments, salles, racks, énergie et câblage ;
- IPAM : préfixes, adresses, VRF, VLAN et DDI ;
- ITAM : organisations, filiales, partenaires, actifs, contrats et licences ;
- Discovery : profils, collecteurs, jobs, preuves et réconciliation ;
- Data : imports, exports et traitements asynchrones ;
- Intégrations : connecteurs externes ;
- Sécurité : identité, rôles, audit et conformité.

## Jeton d’administration du lab Docker

Le jeton bootstrap est géré par le runtime interne et n'est pas stocké dans `.env`. Pour une commande CLI ponctuelle :

```bash
OPENINFRA_TOKEN="$(python scripts/docker_environment.py bootstrap-token)"
```

Après les opérations, exécuter `unset OPENINFRA_TOKEN`.

## Flux de travail métier

Créer les objets dans l’ordre de dépendance :

1. organisation et filiale/subdivision ;
2. site avec adresse complète ;
3. bâtiment et étages ;
4. salle avec bornes lignes/colonnes ;
5. rack ou châssis ;
6. ressource RSOT et localisation physique ;
7. contrats, garanties, supports et licences associés.

Les champs site, bâtiment, salle, rack, organisation, partenaire, pays et tenant sont des sélections contrôlées. Ne pas contourner ces référentiels par du texte libre.

## Recherche globale

La recherche globale est disponible dans le header. Elle regroupe les résultats par composant et n’affiche que les domaines autorisés pour l’utilisateur courant.

Par API : `GET /api/v1/search/global`.

Exemple CLI :

```bash
openinfra search global \
  --backend postgresql \
  --tenant default \
  --query firewall \
  --token "$OPENINFRA_TOKEN"
```

## Traitements asynchrones

Les imports massifs, exports, graphes et traitements RAG sont exécutés hors du chemin HTTP interactif. Après soumission :

1. conserver l’identifiant de job ;
2. consulter son état ;
3. télécharger l’artefact résultat après succès ;
4. signaler tout passage en DLQ à un administrateur.

```bash
openinfra async jobs \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN"
```

## Accessibilité

L’interface vise WCAG 2.2 AA : navigation clavier, focus visible, libellés associés, messages d’erreur textuels et structure sémantique. Les informations ne reposent pas uniquement sur la couleur. Le zoom navigateur et les technologies d’assistance doivent rester compatibles avec la navigation responsive.

Pour signaler un défaut, fournir la page, le composant, l’action, le navigateur, le niveau de zoom, la technologie d’assistance et le résultat attendu.
