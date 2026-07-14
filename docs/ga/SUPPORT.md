# Support, maintenance et cycle de vie

Version cible : `0.33.3`

## Périmètre du support

Le dispositif OpenInfra distingue les éditions Lite, Pro et Enterprise. Les objectifs publiés ici sont des objectifs opérationnels du projet ; un contrat de service signé peut définir des engagements plus stricts. Le support couvre le diagnostic, les correctifs, les avis de sécurité, la compatibilité de mise à niveau et l’accompagnement au retour à un état stable. Il ne remplace pas l’exploitation de l’infrastructure cliente, la sauvegarde PostgreSQL ni la surveillance locale.

## Sévérités S1 à S4

- **S1 critique** : indisponibilité de production, perte d’intégrité, exposition de sécurité active ou absence totale de contournement.
- **S2 élevée** : fonction majeure dégradée, impact étendu ou contournement instable.
- **S3 moyenne** : défaut limité avec contournement viable et sans risque immédiat sur les données.
- **S4 faible** : question, demande d’amélioration, défaut cosmétique ou documentation.

Le niveau est déterminé à partir de l’impact, de l’urgence, du nombre d’utilisateurs touchés, de la disponibilité d’un contournement et du risque sur les données. Un ticket peut être reclassé lorsque les faits changent. Les délais de réponse, de mise à jour et de restauration sont définis dans `docs/release/support-maintenance-policy.json`.

## Canaux et collecte minimale

Toute demande doit contenir la version `openinfra version`, l’édition, l’environnement, l’heure UTC du début d’incident, le résultat des endpoints `/health` et `/ready`, les logs expurgés et les changements récents. Aucun secret, jeton, mot de passe, clé privée ou export de données métier ne doit être joint. Les éditions Pro et Enterprise utilisent le portail de support ; Enterprise dispose en plus du canal téléphonique pour S1 et S2.

```powershell
openinfra version
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=200 api web migrate
curl.exe -f http://127.0.0.1:8080/health
curl.exe -f http://127.0.0.1:8080/ready
```

## Cycle de vie des versions

Une version mineure traverse quatre états : active, maintenance, sécurité uniquement et fin de vie. La phase active accepte fonctionnalités compatibles, corrections et sécurité. La maintenance accepte les corrections et la sécurité. La phase sécurité uniquement ne reçoit que les correctifs de vulnérabilités supportées. Une version en fin de vie ne reçoit aucun correctif et doit être migrée. Le calendrier de référence est de douze mois actifs, six mois de maintenance puis six mois de sécurité uniquement.

Les correctifs utilisent une version de patch. Les changements incompatibles nécessitent une version majeure et une procédure de migration documentée. Les avis de dépréciation sont publiés avant suppression et indiquent la solution de remplacement.

## Politique de correctifs

Une vulnérabilité critique impose une mitigation sous vingt-quatre heures et une cible de correctif sous trois jours. Les vulnérabilités élevées visent une mitigation sous soixante-douze heures et un correctif sous quatorze jours. Les niveaux moyen et faible suivent respectivement des cibles de soixante et cent quatre-vingts jours. Chaque correctif doit passer les tests, le scan de sécurité, le packaging reproductible, la validation de migration et le smoke test installé.

## Mise à niveau et migration

La mise à niveau directe est supportée entre deux versions mineures consécutives. Un écart de deux versions mineures exige un passage intermédiaire. Au-delà, un plan de migration approuvé est obligatoire. Une sauvegarde vérifiée, un contrôle d’espace, la validation des migrations et une stratégie de rollback sont obligatoires avant modification. Les détails opératoires sont décrits dans [UPGRADE.md](UPGRADE.md).

## Escalade et communication

Le niveau L1 qualifie et collecte les preuves. L2 reproduit le défaut et construit le contournement ou le correctif. L3 associe SRE et sécurité pour les incidents de cluster, d’intégrité ou de cybersécurité. Un incident commander coordonne les S1 Enterprise, les impacts multi-clients et les avis publics. Toute communication d’incident indique l’état, l’impact, les actions en cours, l’heure de prochaine mise à jour et la décision de clôture.

## Maintenance planifiée

Une maintenance planifiée comprend une fenêtre, un responsable, une sauvegarde récente, un plan de retour arrière, des critères de succès et une communication préalable. Les migrations de schéma sont appliquées par le service `migrate` avant le redémarrage applicatif. Une maintenance n’est clôturée qu’après validation de `/ready`, de l’interface web, des workers asynchrones et des métriques critiques.
