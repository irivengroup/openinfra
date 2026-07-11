# Organisation de Swagger et ReDoc

Le contrat OpenAPI canonique est organisé selon une taxonomie unique :

```text
Composant
└── Contexte métier
    └── Endpoints
```

## Rendu

- **ReDoc** consomme l'extension `x-tagGroups` et affiche un premier niveau par composant, puis les contextes métier associés.
- **Swagger UI** affiche un groupe repliable par couple `Composant · Contexte`. Les groupes sont triés selon l'ordre métier OpenInfra, puis alphabétiquement à l'intérieur de chaque composant.
- Chaque opération possède exactement un tag, un champ `x-openinfra-component` et un champ `x-openinfra-context`.
- Les routes et les schémas de requête/réponse ne sont pas modifiés par cette organisation.

## Règles de rattachement

- Les certificats, endpoints TLS et contrôles PKI restent sous **Sécurité**.
- Les flux déclarés, flux observés, matrice de conformité et configurations réseau restent sous **IPAM**.
- Les dépendances et analyses de graphe restent sous **RSOT**.
- Les fonctions de reprise d'activité et de discovery régional restent sous **Multisite**.
- Un endpoint ne peut pas être publié sans contexte déclaré dans `OpenApiDocumentationTaxonomy`.

## Contrôles

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/integration/test_openapi_yaml_validation.py \
  tests/integration/test_http_api.py

python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
```

Les tests vérifient que les deux contrats contiennent la même taxonomie, que tous les tags sont déclarés une seule fois et que les 300 opérations ou plus sont rattachées à un contexte unique.
