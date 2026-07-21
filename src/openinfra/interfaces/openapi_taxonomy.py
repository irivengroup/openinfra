from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenApiDocumentationContext:
    component: str
    context: str
    description: str

    @property
    def tag(self) -> str:
        return f"{self.component} · {self.context}"


class OpenApiDocumentationTaxonomy:
    _CONTEXTS: tuple[OpenApiDocumentationContext, ...] = (
        OpenApiDocumentationContext(
            "Plateforme",
            "Exploitation et documentation",
            "Découverte API, documentation, santé, disponibilité et version du runtime.",
        ),
        OpenApiDocumentationContext(
            "Plateforme",
            "Licence runtime",
            "Statut, activation et renouvellement offline des licences Pro et Entreprise.",
        ),
        OpenApiDocumentationContext(
            "Plateforme",
            "Observabilité et capacité",
            "Métriques Prometheus, télémétrie runtime et qualification de capacité.",
        ),
        OpenApiDocumentationContext(
            "Plateforme", "Référentiels", "Référentiels transverses publiés par la plateforme."
        ),
        OpenApiDocumentationContext(
            "Plateforme",
            "Base de données",
            "État du schéma PostgreSQL ou Oracle et routage primaire/réplique PostgreSQL.",
        ),
        OpenApiDocumentationContext(
            "Plateforme", "Recherche globale", "Recherche transverse dans les composants autorisés."
        ),
        OpenApiDocumentationContext(
            "Plateforme",
            "Éditions et capacités",
            "Politiques, capacités et quotas des éditions OpenInfra.",
        ),
        OpenApiDocumentationContext(
            "Plateforme",
            "Traitements asynchrones",
            "Outbox transactionnelle, workers spécialisés, artefacts et files de reprise.",
        ),
        OpenApiDocumentationContext(
            "Sécurité",
            "Authentification fédérée",
            "Assertions SAML 2.0 validées depuis la configuration de confiance du serveur.",
        ),
        OpenApiDocumentationContext(
            "Sécurité",
            "Synchronisation des équipes",
            "Synchronisation idempotente LDAP, OAuth, Auth Proxy et Okta.",
        ),
        OpenApiDocumentationContext(
            "Sécurité",
            "Authentification et jetons",
            "Identité courante et cycle de vie des jetons applicatifs.",
        ),
        OpenApiDocumentationContext(
            "Sécurité",
            "Identités et groupes",
            "Utilisateurs, groupes, appartenances et rôles effectifs.",
        ),
        OpenApiDocumentationContext(
            "Sécurité",
            "Autorisations",
            "Règles d'accès et évaluation des décisions d'autorisation.",
        ),
        OpenApiDocumentationContext(
            "Sécurité",
            "Audit et traçabilité",
            "Événements d'audit, export et vérification d'intégrité.",
        ),
        OpenApiDocumentationContext(
            "Sécurité", "Inventaire PKI", "Inventaire et cycle de vie des certificats."
        ),
        OpenApiDocumentationContext(
            "Sécurité", "Endpoints TLS", "Observation des endpoints TLS associés aux certificats."
        ),
        OpenApiDocumentationContext(
            "Sécurité", "Conformité PKI", "Évaluation de la conformité et des échéances PKI."
        ),
        OpenApiDocumentationContext(
            "DCIM", "Sites et bâtiments", "Sites, bâtiments, étages et leur cycle de vie."
        ),
        OpenApiDocumentationContext(
            "DCIM",
            "Espaces et implantation",
            "Salles, zones et localisation physique des équipements.",
        ),
        OpenApiDocumentationContext(
            "DCIM", "Racks et capacité", "Racks, élévations et capacités physiques disponibles."
        ),
        OpenApiDocumentationContext(
            "DCIM",
            "Câblage et connectivité",
            "Panneaux, ports, câbles, traçage et vérification terrain.",
        ),
        OpenApiDocumentationContext(
            "DCIM",
            "Énergie et refroidissement",
            "Puissance, circuits, réservations, refroidissement et capacités.",
        ),
        OpenApiDocumentationContext(
            "DCIM",
            "Topologie et jumeau numérique",
            "Catalogue topologique et représentations numériques du datacenter.",
        ),
        OpenApiDocumentationContext(
            "RSOT",
            "Ressources et versions",
            "Taxonomie, objets de référence, versions et rapprochement.",
        ),
        OpenApiDocumentationContext(
            "RSOT",
            "Relations et dépendances",
            "Relations, graphes, chemins, impacts et points uniques de défaillance.",
        ),
        OpenApiDocumentationContext(
            "RSOT",
            "Qualité et gouvernance",
            "Qualité des données, règles de gouvernance et évaluations.",
        ),
        OpenApiDocumentationContext(
            "IPAM",
            "Adressage et allocations",
            "Adresses, plages, allocations et réservations guidées.",
        ),
        OpenApiDocumentationContext(
            "IPAM", "VRF, préfixes et capacité", "VRF, agrégats, préfixes et analyses de capacité."
        ),
        OpenApiDocumentationContext(
            "IPAM", "VLAN et VXLAN", "Groupes VLAN, VLAN et identifiants VXLAN VNI."
        ),
        OpenApiDocumentationContext(
            "IPAM", "Routage et topologie", "ASN, voisins BGP, liaisons réseau et topologie."
        ),
        OpenApiDocumentationContext(
            "IPAM", "DNS, DHCP et conflits", "Observations DNS, baux DHCP et détection de conflits."
        ),
        OpenApiDocumentationContext(
            "IPAM", "Expérience opérateur", "Vues de pilotage et recherche métier IPAM."
        ),
        OpenApiDocumentationContext(
            "IPAM", "Aperçu DDI", "Prévisualisation des changements DNS, DHCP et IPAM."
        ),
        OpenApiDocumentationContext(
            "IPAM", "Flux déclarés", "Déclaration et retrait des flux réseau attendus."
        ),
        OpenApiDocumentationContext(
            "IPAM", "Flux observés", "Ingestion et consultation des flux réseau observés."
        ),
        OpenApiDocumentationContext(
            "IPAM", "Conformité des flux", "Matrice de comparaison entre flux déclarés et observés."
        ),
        OpenApiDocumentationContext(
            "IPAM",
            "Conformité réseau",
            "Golden configurations, observations et évaluation de dérive réseau.",
        ),
        OpenApiDocumentationContext(
            "Discovery",
            "Évidences et rapprochement",
            "Évidences collectées, rapprochements et résolution.",
        ),
        OpenApiDocumentationContext(
            "Discovery",
            "Collecteurs et profils",
            "Collecteurs, profils de protocoles, intégrations et enrôlements.",
        ),
        OpenApiDocumentationContext(
            "Discovery",
            "Orchestration des jobs",
            "Création, attribution, renouvellement, terminaison et reprise des jobs.",
        ),
        OpenApiDocumentationContext(
            "Discovery",
            "Kubernetes et cloud-native",
            "Inventaire Kubernetes versionné, topologie applicative et mapping physique "
            "jusqu'au site.",
        ),
        OpenApiDocumentationContext(
            "ITAM",
            "Organisations et subdivisions",
            "Organisations, filiales et subdivisions propriétaires.",
        ),
        OpenApiDocumentationContext(
            "ITAM",
            "Partenaires et support",
            "Partenaires, constructeurs, éditeurs et couvertures de support.",
        ),
        OpenApiDocumentationContext(
            "ITAM", "Licences logicielles", "Licences, affectations et conformité logicielle."
        ),
        OpenApiDocumentationContext(
            "Intégrations", "ITSM et CMDB", "Connecteurs ITSM/CMDB et plans de synchronisation."
        ),
        OpenApiDocumentationContext(
            "Import et export", "Exports", "Génération et téléchargement d'exports gouvernés."
        ),
        OpenApiDocumentationContext(
            "Import et export", "Imports", "Chargement, validation, suivi et rollback des imports."
        ),
        OpenApiDocumentationContext(
            "Import et export", "Migrations", "Modèles, guides, plans et rapports de migration."
        ),
        OpenApiDocumentationContext(
            "Opérations terrain",
            "Fiches d'intervention",
            "Génération et cycle de vie des fiches d'intervention.",
        ),
        OpenApiDocumentationContext(
            "Opérations terrain", "Preuves terrain", "Pièces de preuve, rattachement et validation."
        ),
        OpenApiDocumentationContext(
            "Opérations terrain", "Codes QR", "Vérification des codes QR d'identification terrain."
        ),
        OpenApiDocumentationContext(
            "Opérations terrain",
            "Verrous d'intervention",
            "Acquisition et libération des verrous d'intervention.",
        ),
        OpenApiDocumentationContext(
            "Opérations terrain",
            "Synchronisation hors ligne",
            "Création et synchronisation des paquets hors ligne.",
        ),
        OpenApiDocumentationContext(
            "Simulation", "Scénarios", "Création, exécution et annulation de simulations."
        ),
        OpenApiDocumentationContext(
            "Simulation",
            "Rapports d'impact",
            "Consultation des rapports d'impact issus des simulations.",
        ),
        OpenApiDocumentationContext(
            "Simulation", "Comparaisons", "Comparaison déterministe des scénarios simulés."
        ),
        OpenApiDocumentationContext(
            "FinOps", "Allocation des coûts", "Règles d'allocation et gouvernance des coûts."
        ),
        OpenApiDocumentationContext(
            "FinOps", "Ingestion des coûts", "Imports et enregistrements de coûts normalisés."
        ),
        OpenApiDocumentationContext(
            "FinOps", "Budgets et clôtures", "Budgets et clôture des périodes financières."
        ),
        OpenApiDocumentationContext(
            "FinOps", "Rapports", "Génération, consultation et export des rapports FinOps."
        ),
        OpenApiDocumentationContext(
            "FinOps", "Analyses et prévisions", "Anomalies et prévisions de coûts."
        ),
        OpenApiDocumentationContext(
            "GreenOps",
            "Sources et facteurs carbone",
            "Sources de mesure et facteurs d'émission carbone.",
        ),
        OpenApiDocumentationContext(
            "GreenOps", "Politiques et mesures", "Politiques GreenOps et mesures énergétiques."
        ),
        OpenApiDocumentationContext(
            "GreenOps", "Rapports", "Génération, consultation et export des rapports GreenOps."
        ),
        OpenApiDocumentationContext(
            "GreenOps",
            "Optimisation et prévisions",
            "Anomalies, prévisions, consolidations et scores GreenOps.",
        ),
        OpenApiDocumentationContext(
            "RAG", "Documents et index", "Documents de connaissance et indexation des données RSOT."
        ),
        OpenApiDocumentationContext(
            "RAG", "Requêtes et réponses", "Questions contextualisées et réponses traçables."
        ),
        OpenApiDocumentationContext(
            "RAG", "Jobs et artefacts", "Jobs RAG, exécution et artefacts produits."
        ),
        OpenApiDocumentationContext(
            "SBOM", "Documents et vulnérabilités", "Documents SBOM et vulnérabilités importées."
        ),
        OpenApiDocumentationContext(
            "SBOM", "Expositions et risques", "Expositions, constats et évaluation des risques."
        ),
        OpenApiDocumentationContext(
            "SBOM", "Comparaisons", "Comparaison de versions et dérives SBOM."
        ),
        OpenApiDocumentationContext(
            "Multisite", "Accès et sites", "Affectations locales et périmètres de sites."
        ),
        OpenApiDocumentationContext(
            "Multisite", "Rapports consolidés", "Rapports consolidés sur plusieurs sites."
        ),
        OpenApiDocumentationContext(
            "Multisite", "Reprise d'activité", "Plans et exercices de reprise d'activité multisite."
        ),
        OpenApiDocumentationContext(
            "Multisite", "Discovery régional", "Routage régional des jobs Discovery Enterprise."
        ),
    )

    @classmethod
    def contexts(cls) -> tuple[OpenApiDocumentationContext, ...]:
        return cls._CONTEXTS

    @classmethod
    def component_order(cls) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.component for item in cls._CONTEXTS))

    @classmethod
    def tags(cls) -> tuple[str, ...]:
        return tuple(item.tag for item in cls._CONTEXTS)

    @classmethod
    def context_for_path(cls, path: str) -> OpenApiDocumentationContext:
        component, context = cls._classify(path)
        for item in cls._CONTEXTS:
            if item.component == component and item.context == context:
                return item
        raise ValueError(
            f"OpenAPI taxonomy context is not declared for {path}: {component} / {context}"
        )

    @classmethod
    def _classify(cls, path: str) -> tuple[str, str]:
        if path in {
            "/",
            "/api/v1",
            "/docs",
            "/swagger",
            "/redoc",
            "/openapi.yaml",
            "/api/v1/openapi.yaml",
            "/health",
            "/ready",
            "/api/v1/version",
        }:
            return "Plateforme", "Exploitation et documentation"
        if path.startswith("/api/v1/license/"):
            return "Plateforme", "Licence runtime"
        if path == "/metrics":
            return "Plateforme", "Observabilité et capacité"
        if path.startswith("/api/v1/reference/"):
            return "Plateforme", "Référentiels"
        if path.startswith("/api/v1/database/"):
            return "Plateforme", "Base de données"
        if path.startswith("/api/v1/search/"):
            return "Plateforme", "Recherche globale"
        if path.startswith("/api/v1/editions/"):
            return "Plateforme", "Éditions et capacités"
        if path.startswith("/api/v1/async/"):
            return "Plateforme", "Traitements asynchrones"
        if path.startswith("/api/v1/security/"):
            return "Sécurité", "Authentification et jetons"
        if path == "/api/v1/auth/saml/acs":
            return "Sécurité", "Authentification fédérée"
        if path == "/api/v1/identity/team-sync":
            return "Sécurité", "Synchronisation des équipes"
        if path.startswith("/api/v1/identity/"):
            return "Sécurité", "Identités et groupes"
        if path.startswith("/api/v1/access/"):
            return "Sécurité", "Autorisations"
        if path.startswith("/api/v1/audit/"):
            return "Sécurité", "Audit et traçabilité"
        if path.startswith("/api/v1/certificates"):
            if "/assessment" in path:
                return "Sécurité", "Conformité PKI"
            if "/endpoints" in path:
                return "Sécurité", "Endpoints TLS"
            return "Sécurité", "Inventaire PKI"
        if path.startswith("/api/v1/dcim/"):
            suffix = path.removeprefix("/api/v1/dcim/")
            if suffix.startswith(("site", "building", "floor")):
                return "DCIM", "Sites et bâtiments"
            if suffix.startswith(("room", "zone", "location", "locator-sheet")):
                return "DCIM", "Espaces et implantation"
            if suffix.startswith("rack"):
                return "DCIM", "Racks et capacité"
            if suffix.startswith(("patch-panel", "ports", "cables", "cable-trace", "verify-scan")):
                return "DCIM", "Câblage et connectivité"
            if suffix.startswith(("power-", "cooling-", "energy-")):
                return "DCIM", "Énergie et refroidissement"
            if suffix.startswith(("topology-catalog", "digital-twin")):
                return "DCIM", "Topologie et jumeau numérique"
        if path.startswith("/api/v1/graph/"):
            return "RSOT", "Relations et dépendances"
        if path.startswith("/api/v1/rsot/"):
            suffix = path.removeprefix("/api/v1/rsot/")
            if suffix.startswith(("resource-taxonomy", "objects", "object-", "reconcile-object")):
                return "RSOT", "Ressources et versions"
            if suffix.startswith("relations"):
                return "RSOT", "Relations et dépendances"
            if suffix.startswith(("quality/", "governance")):
                return "RSOT", "Qualité et gouvernance"
        if path == "/api/v1/ipam/allocate" or path.startswith(
            ("/api/v1/ipam/addresses", "/api/v1/ipam/ranges", "/api/v1/ipam/reservation-wizard")
        ):
            return "IPAM", "Adressage et allocations"
        if path.startswith(
            (
                "/api/v1/ipam/vrfs",
                "/api/v1/ipam/aggregates",
                "/api/v1/ipam/prefixes",
                "/api/v1/ipam/capacity",
            )
        ):
            return "IPAM", "VRF, préfixes et capacité"
        if path.startswith(
            ("/api/v1/ipam/vlan-groups", "/api/v1/ipam/vlans", "/api/v1/ipam/vxlan-vnis")
        ):
            return "IPAM", "VLAN et VXLAN"
        if path.startswith(
            (
                "/api/v1/ipam/asns",
                "/api/v1/ipam/bgp-peers",
                "/api/v1/ipam/network-bindings",
                "/api/v1/ipam/topology",
            )
        ):
            return "IPAM", "Routage et topologie"
        if path.startswith(
            ("/api/v1/ipam/dns-observations", "/api/v1/ipam/dhcp-leases", "/api/v1/ipam/conflicts")
        ):
            return "IPAM", "DNS, DHCP et conflits"
        if path.startswith("/api/v1/ipam/ui-"):
            return "IPAM", "Expérience opérateur"
        if path.startswith("/api/v1/ipam/ddi-preview"):
            return "IPAM", "Aperçu DDI"
        if path.startswith("/api/v1/flows/declarations"):
            return "IPAM", "Flux déclarés"
        if path.startswith("/api/v1/flows/observations"):
            return "IPAM", "Flux observés"
        if path.startswith("/api/v1/flows/matrix"):
            return "IPAM", "Conformité des flux"
        if path.startswith("/api/v1/network-config/"):
            return "IPAM", "Conformité réseau"
        if path.startswith("/api/v1/exports/"):
            return "Import et export", "Exports"
        if path.startswith("/api/v1/imports/migration-"):
            return "Import et export", "Migrations"
        if path.startswith("/api/v1/imports/"):
            return "Import et export", "Imports"
        if path.startswith(("/api/v1/discovery/evidence", "/api/v1/discovery/reconciliation")):
            return "Discovery", "Évidences et rapprochement"
        if path.startswith(
            (
                "/api/v1/discovery/collectors",
                "/api/v1/discovery/protocol-",
                "/api/v1/discovery/integration-",
                "/api/v1/discovery/local-plan",
                "/api/v1/discovery/agent-bootstrap-plan",
                "/api/v1/discovery/proxy-enrollments",
            )
        ):
            return "Discovery", "Collecteurs et profils"
        if path.startswith(("/api/v1/discovery/job", "/api/v1/discovery/jobs")):
            return "Discovery", "Orchestration des jobs"
        if path.startswith(
            (
                "/api/v1/kubernetes/topologies",
                "/api/v1/kubernetes/gitops-states",
            )
        ):
            return "Discovery", "Kubernetes et cloud-native"
        if path.startswith(
            (
                "/api/v1/itam/organization",
                "/api/v1/itam/organizations",
                "/api/v1/itam/tenant",
                "/api/v1/itam/tenants",
            )
        ):
            return "ITAM", "Organisations et subdivisions"
        if path.startswith(
            ("/api/v1/itam/partner", "/api/v1/itam/partners", "/api/v1/itam/support-")
        ):
            return "ITAM", "Partenaires et support"
        if path.startswith("/api/v1/itam/software-license"):
            return "ITAM", "Licences logicielles"
        if path.startswith("/api/v1/integrations/itsm/"):
            return "Intégrations", "ITSM et CMDB"
        if path.startswith("/api/v1/field-operation-sheets"):
            return "Opérations terrain", "Fiches d'intervention"
        if path.startswith("/api/v1/field-evidence"):
            return "Opérations terrain", "Preuves terrain"
        if path.startswith("/api/v1/qr-codes"):
            return "Opérations terrain", "Codes QR"
        if path.startswith("/api/v1/intervention-locks"):
            return "Opérations terrain", "Verrous d'intervention"
        if path.startswith("/api/v1/offline-sync-packages"):
            return "Opérations terrain", "Synchronisation hors ligne"
        if path.startswith("/api/v1/simulation-scenarios"):
            return "Simulation", "Scénarios"
        if path.startswith("/api/v1/impact-reports"):
            return "Simulation", "Rapports d'impact"
        if path.startswith("/api/v1/scenario-comparisons"):
            return "Simulation", "Comparaisons"
        if path.startswith("/api/v1/finops/allocation-rules"):
            return "FinOps", "Allocation des coûts"
        if path.startswith(("/api/v1/finops/import-jobs", "/api/v1/finops/cost-records")):
            return "FinOps", "Ingestion des coûts"
        if path.startswith(("/api/v1/finops/budgets", "/api/v1/finops/periods")):
            return "FinOps", "Budgets et clôtures"
        if path.startswith("/api/v1/finops/reports"):
            return "FinOps", "Rapports"
        if path.startswith(("/api/v1/finops/anomalies", "/api/v1/finops/forecasts")):
            return "FinOps", "Analyses et prévisions"
        if path.startswith(
            ("/api/v1/greenops/measurement-sources", "/api/v1/greenops/carbon-factors")
        ):
            return "GreenOps", "Sources et facteurs carbone"
        if path.startswith(("/api/v1/greenops/policies", "/api/v1/greenops/energy-measurements")):
            return "GreenOps", "Politiques et mesures"
        if path.startswith("/api/v1/greenops/reports"):
            return "GreenOps", "Rapports"
        if path.startswith(
            (
                "/api/v1/greenops/anomalies",
                "/api/v1/greenops/capacity-forecasts",
                "/api/v1/greenops/consolidation-candidates",
                "/api/v1/greenops/green-scores",
            )
        ):
            return "GreenOps", "Optimisation et prévisions"
        if path.startswith(("/api/v1/rag/documents", "/api/v1/rag/index/")):
            return "RAG", "Documents et index"
        if path.startswith(("/api/v1/rag/query", "/api/v1/rag/answers")):
            return "RAG", "Requêtes et réponses"
        if path.startswith("/api/v1/rag/jobs"):
            return "RAG", "Jobs et artefacts"
        if path.startswith(("/api/v1/sbom/documents", "/api/v1/sbom/vulnerabilities")):
            return "SBOM", "Documents et vulnérabilités"
        if path.startswith(
            ("/api/v1/sbom/exposures", "/api/v1/sbom/findings", "/api/v1/sbom/risk/")
        ):
            return "SBOM", "Expositions et risques"
        if path.startswith("/api/v1/sbom/comparisons"):
            return "SBOM", "Comparaisons"
        if path.startswith(("/api/v1/multisite/site-access", "/api/v1/multisite/sites")):
            return "Multisite", "Accès et sites"
        if path.startswith("/api/v1/multisite/reports"):
            return "Multisite", "Rapports consolidés"
        if path.startswith("/api/v1/multisite/disaster-recovery"):
            return "Multisite", "Reprise d'activité"
        if path.startswith("/api/v1/multisite/regional-discovery"):
            return "Multisite", "Discovery régional"
        raise ValueError(f"OpenAPI path is not classified: {path}")
