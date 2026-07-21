# ADR-0018 — Runtime ASGI haute performance

## Statut
Accepté — CDC 4.9.0, OpenInfra 0.30.0.

## Contexte
Le serveur HTTP historique crée un thread par requête et ne fournit ni workers multiprocessus natifs, ni backpressure, ni gestion moderne du cycle de vie. Ce plafond est incompatible avec les objectifs Pro et Entreprise.

## Décision
Les services API et Web utilisent ASGI et Uvicorn par défaut. Ils sont stateless, multiprocessus et déployables en plusieurs réplicas derrière un répartiteur. Le code métier synchrone existant est exécuté dans un threadpool borné pendant la transition ; les nouveaux adaptateurs peuvent devenir nativement asynchrones sans modifier le domaine.

Le runtime `legacy` est maintenu uniquement comme rollback contrôlé et doit rester testé. Il n’est pas la cible de production Pro/Entreprise.

## Conséquences
- backpressure et limites de concurrence configurables ;
- arrêt propre par lifespan ASGI ;
- compatibilité des contrats HTTP ;
- nécessité de dimensionner workers, pools et connexions comme un budget global ;
- aucune multiplication de microservices sans bénéfice démontré.
