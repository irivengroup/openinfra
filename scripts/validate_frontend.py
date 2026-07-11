from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


class FrontendValidationError(Exception):
    """Raised when the OpenInfra frontend contract is incomplete."""


@dataclass(frozen=True, slots=True)
class FrontendValidationReport:
    project_root: Path
    react_declared: bool
    bootstrap_declared: bool
    compose_web_service: bool
    static_assets: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "project_root": str(self.project_root),
            "react_declared": self.react_declared,
            "bootstrap_declared": self.bootstrap_declared,
            "compose_web_service": self.compose_web_service,
            "static_assets": list(self.static_assets),
            "valid": True,
        }


class FrontendContractValidator:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()

    def validate(self) -> FrontendValidationReport:
        package = self._read_json(self._project_root / "web/package.json")
        scripts = package.get("scripts", {})
        if not isinstance(scripts, dict):
            raise FrontendValidationError("web/package.json scripts must be an object")
        required_accessibility_scripts = {"a11y", "a11y:jsx"}
        missing_accessibility_scripts = sorted(required_accessibility_scripts - set(scripts))
        if missing_accessibility_scripts:
            raise FrontendValidationError(
                "web/package.json accessibility scripts are incomplete: "
                + ", ".join(missing_accessibility_scripts)
            )
        dependencies = package.get("dependencies", {})
        if not isinstance(dependencies, dict):
            raise FrontendValidationError("web/package.json dependencies must be an object")
        react_declared = "react" in dependencies and "react-dom" in dependencies
        bootstrap_declared = "bootstrap" in dependencies
        if not react_declared:
            raise FrontendValidationError("web/package.json must declare React and React DOM")
        if not bootstrap_declared:
            raise FrontendValidationError("web/package.json must declare Bootstrap 5")
        main_source = (self._project_root / "web/src/main.jsx").read_text(encoding="utf-8")
        i18n_source = (self._project_root / "web/src/i18n.js").read_text(encoding="utf-8")
        if (
            "from 'react'" not in main_source
            or "bootstrap/dist/css/bootstrap.min.css" not in main_source
            or "openinfra-theme.css" not in main_source
            or "const pageTitle = activeModuleId === 'overview' ? 'Dashboard'" not in main_source
            or "activeModuleId === 'overview' &&" not in main_source
            or "Dashboard de pilotage OpenInfra" in main_source
            or "openinfra-accordion" not in main_source
            or "openinfra-compact-menu-button" not in main_source
            or "openinfra-mobile-menu-icon" not in main_source
            or "mobileSidebarOpen" not in main_source
            or "i18n.t('componentStatistics')" not in main_source
            or "openinfra-pie-chart" not in main_source
            or "fetch('/status'" not in main_source
            or "i18n.t('forms')" not in main_source
            or "Numéro de série" not in main_source
            or "Catalogue catégories / types" not in main_source
            or "RESOURCE_TAXONOMY" not in main_source
            or "RESOURCE_CATEGORY_OPTIONS" not in main_source
            or "Rack server" not in main_source
            or "physical-server" in main_source
            or "Inventaire PKI" not in main_source
            or "/v1/certificates/import" not in main_source
            or "/v1/certificates/get" not in main_source
            or "/v1/certificates/endpoints/observe" not in main_source
            or "/v1/certificates/assessment" not in main_source
            or "Dashboard IPAM" not in main_source
            or "/v1/ipam/ui-dashboard" not in main_source
            or "Définir une VRF" not in main_source
            or "/v1/ipam/vrfs" not in main_source
            or "Définir un agrégat IP" not in main_source
            or "/v1/ipam/aggregates" not in main_source
            or "Définir un préfixe IP" not in main_source
            or "/v1/ipam/prefixes" not in main_source
            or "Définir une plage IP" not in main_source
            or "/v1/ipam/ranges" not in main_source
            or "Enregistrer une adresse IP" not in main_source
            or "/v1/ipam/addresses" not in main_source
            or "Assistant de réservation IP" not in main_source
            or "/v1/ipam/reservation-wizard" not in main_source
            or "Afficher les bindings réseau" not in main_source
            or "/v1/ipam/network-bindings" not in main_source
            or "Topologie opérationnelle IPAM" not in main_source
            or "/v1/ipam/topology" not in main_source
            or "Définir un groupe VLAN" not in main_source
            or "/v1/ipam/vlan-groups" not in main_source
            or "Définir un VXLAN VNI" not in main_source
            or "/v1/ipam/vxlan-vnis" not in main_source
            or "Définir un VLAN" not in main_source
            or "/v1/ipam/vlans" not in main_source
            or "Définir un ASN" not in main_source
            or "/v1/ipam/asns" not in main_source
            or "Définir un peer BGP" not in main_source
            or "/v1/ipam/bgp-peers" not in main_source
            or "Observer un enregistrement DNS" not in main_source
            or "/v1/ipam/dns-observations" not in main_source
            or "Observer un bail DHCP" not in main_source
            or "/v1/ipam/dhcp-leases" not in main_source
            or "Prévisualiser DDI" not in main_source
            or "/v1/ipam/ddi-preview" not in main_source
            or "RT import" not in main_source
            or "Fournisseurs DDI" not in main_source
            or "Localiser un équipement" not in main_source
            or "/v1/dcim/locations" not in main_source
            or "Élévation rack" not in main_source
            or "/v1/dcim/rack-elevation" not in main_source
            or "Définir un panneau de brassage" not in main_source
            or "/v1/dcim/patch-panels" not in main_source
            or "Définir un port DCIM" not in main_source
            or "/v1/dcim/ports" not in main_source
            or "Connecter un câble" not in main_source
            or "/v1/dcim/cables" not in main_source
            or "Définir un équipement électrique" not in main_source
            or "/v1/dcim/power-devices" not in main_source
            or "Définir un circuit électrique" not in main_source
            or "/v1/dcim/power-circuits" not in main_source
            or "Définir une zone de refroidissement" not in main_source
            or "/v1/dcim/cooling-zones" not in main_source
            or "Réserver la puissance équipement" not in main_source
            or "/v1/dcim/power-reservations" not in main_source
            or "Capacité énergie/refroidissement" not in main_source
            or "/v1/dcim/energy-cooling-capacity" not in main_source
            or "Jumeau numérique salle" not in main_source
            or "/v1/dcim/digital-twin" not in main_source
            or "Chemin câble" not in main_source
            or "Format rendu" not in main_source
            or "Face rack" not in main_source
            or "IT Asset Management" not in main_source
            or "ITAM" not in main_source
            or "icon: 'asset'" not in main_source
            or "Tenant de sécurité" in main_source
            or "/v1/itam/support-profile" not in main_source
            or "/v1/itam/support-coverage" not in main_source
            or "Déclarer garantie constructeur" not in main_source
            or "Ajouter support tiers" not in main_source
            or "MODULES.map((module, index)" not in main_source
            or "MODULES.slice(0, 6)" in main_source
            or "Token API" in main_source
            or "openinfra-skip-link" not in main_source
            or "i18n.t('skipToContent')" not in main_source
            or "openinfra-main-content" not in main_source
            or "aria-current" not in main_source
            or 'role="listbox"' not in main_source
            or 'role="option"' not in main_source
            or "aria-live" not in main_source
            or "aria-autocomplete" not in main_source
            or "shouldFocusMain" not in main_source
            or "openinfra-edition-badge" not in main_source
            or "config.authMode || 'standard'" in main_source
            or "Politiques éditions et quotas" not in main_source
            or "/v1/editions/policies" not in main_source
            or "/v1/editions/feature-check" not in main_source
            or "/v1/editions/quota-check" not in main_source
            or "Guide migration données" not in main_source
            or "/v1/imports/migration-guide" not in main_source
            or "Chunk export signé" not in main_source
            or "/v1/exports/artifact-chunk" not in main_source
            or "badge text-bg-primary openinfra-edition-badge" in main_source
        ):
            raise FrontendValidationError(
                "web/src/main.jsx must implement the OpenInfra React + Bootstrap dashboard UI"
            )
        self._validate_i18n_contract(main_source, i18n_source)
        for required_header_fragment in (
            "bg-dark text-white",
            "text-small",
            "openinfra-global-toolbar",
            "openinfra-component-nav",
            "openinfra-mega-menu",
            "openinfra-compact-menu-button",
            "openinfra-mobile-menu-icon",
            "openinfra-compact-navigation",
            "openinfra-navigation-backdrop",
            "openinfra-toolbar-actions",
            "isMegamenuViewport",
            "closeResponsiveNavigation",
            "openMegaMenu",
            "openinfra-component-link",
            "onMouseEnter",
            "openinfra-header-stack",
            "syncHeaderOffset",
            "--openinfra-fixed-header-height",
            "openinfra-global-search",
            "i18n.t('globalSearch')",
            "globalSearchGroups",
            "buildGlobalSearchUrl",
            "/v1/search/global",
            "globalSearchBackend",
            "i18n.t('backendSearchUnavailable')",
            "Swagger",
            "ReDoc",
            "apiDocumentation",
            "apiDocumentationLinks",
            "buildApiDocumentationUrl",
            "i18n.t('openSwagger')",
            "i18n.t('openRedoc')",
            "openinfra-api-doc-actions",
            "openinfra-edition-badge",
            "openinfra-skip-link",
            "openinfra-main-content",
            'role="listbox"',
            'role="option"',
            "aria-current",
            "aria-live",
            "aria-autocomplete",
            "openinfra-live-region",
            "skipToNavigation",
            "skipToSearch",
            "componentNavigationInstructions",
            "ArrowRight",
            "ArrowLeft",
            "ArrowDown",
            "opensNewWindow",
        ):
            if required_header_fragment not in main_source:
                raise FrontendValidationError(
                    "web/src/main.jsx must keep the Bootstrap 5 double-header global search theme"
                )
        forbidden_main_source = (
            "Search OpenInfra operations",
            "openinfra-search",
            "Login</button>",
            "Sign-up",
            "Tenant de sécurité",
        )
        leaked_main = [fragment for fragment in forbidden_main_source if fragment in main_source]
        if leaked_main:
            raise FrontendValidationError(
                "web/src/main.jsx must not expose the removed secondary header controls: "
                + ", ".join(leaked_main)
            )
        forbidden_default_alerts = (
            "alert alert-info",
            'role="note"',
            'className="alert alert-info"',
            "background: linear-gradient(135deg, rgba(0, 174, 239, .08)",
            "border: 1px solid rgba(0, 174, 239, .18)",
            "padding: .7rem .8rem !important",
            "openinfra-submit-btn",
            "Formulaire métier typé : chaque champ correspond",
            "Aucun champ générique Attributs",
        )
        leaked_alerts = [
            fragment for fragment in forbidden_default_alerts if fragment in main_source
        ]
        if leaked_alerts:
            raise FrontendValidationError(
                "web/src/main.jsx must not render default informational alerts: "
                + ", ".join(leaked_alerts)
            )
        if "submissionCompleted && activeModuleId !== 'overview' &&" not in main_source:
            raise FrontendValidationError(
                "web/src/main.jsx must keep success alerts conditional on a form submission"
            )
        compose = (self._project_root / "compose.yaml").read_text(encoding="utf-8")
        compose_required = (
            "  web:",
            "container_name: openinfra-web",
            "OPENINFRA_WEB_BACKEND_URL",
            "OPENINFRA_WEB_PUBLIC_API_BASE_URL",
            "OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL",
            "OPENINFRA_WEB_BACKEND_BEARER_TOKEN",
            "OPENINFRA_BOOTSTRAP_TOKEN:?OPENINFRA_BOOTSTRAP_TOKEN is required",
            "http://127.0.0.1:2006/health",
        )
        missing_compose = [fragment for fragment in compose_required if fragment not in compose]
        if missing_compose:
            raise FrontendValidationError(
                "compose.yaml openinfra-web service is incomplete: " + ", ".join(missing_compose)
            )
        assets = self._validate_static_assets()
        return FrontendValidationReport(
            project_root=self._project_root,
            react_declared=react_declared,
            bootstrap_declared=bootstrap_declared,
            compose_web_service=True,
            static_assets=assets,
        )

    def _read_json(self, path: Path) -> dict[str, object]:
        if not path.is_file():
            raise FrontendValidationError("missing frontend file: " + str(path))
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise FrontendValidationError("invalid JSON object: " + str(path))
        return data

    def _validate_i18n_contract(self, main_source: str, i18n_source: str) -> None:
        required_main = (
            "OpenInfraI18n",
            "localizeOpenInfraCatalog",
            'id="openinfra-language"',
            'value="en"',
            'value="fr"',
            "i18n.setLanguage",
            "i18n.translateDom",
        )
        required_i18n = (
            "SUPPORTED_LANGUAGES = Object.freeze(['en', 'fr'])",
            "DEFAULT_LANGUAGE = 'en'",
            "navigatorObject.languages",
            "navigatorObject.language",
            "LANGUAGE_STORAGE_KEY = 'openinfra.language'",
            "Intl.DisplayNames",
            "localizeOpenInfraCatalog",
            "floorName(levelIndex",
            "countryName(alpha2",
        )
        missing = [fragment for fragment in required_main if fragment not in main_source] + [
            fragment for fragment in required_i18n if fragment not in i18n_source
        ]
        if missing:
            raise FrontendValidationError(
                "web interface FR/EN contract is incomplete: " + ", ".join(missing)
            )

    def _validate_static_assets(self) -> tuple[str, ...]:
        root = self._project_root / "src/openinfra/interfaces/rendering/static"
        required = (
            "index.html",
            "assets/bootstrap.min.css",
            "assets/openinfra-i18n.js",
            "assets/openinfra-form-fields.js",
            "assets/openinfra-web.js",
            "assets/openinfra-web.css",
        )
        missing = [name for name in required if not (root / name).is_file()]
        if missing:
            raise FrontendValidationError("missing runtime web assets: " + ", ".join(missing))
        assets_by_name = {name: (root / name).read_text(encoding="utf-8") for name in required}
        payload = "\n".join(assets_by_name.values())
        runtime_js = assets_by_name["assets/openinfra-web.js"]
        runtime_i18n = assets_by_name["assets/openinfra-i18n.js"]
        runtime_form_fields = assets_by_name["assets/openinfra-form-fields.js"]
        source_i18n = (self._project_root / "web/src/i18n.js").read_text(encoding="utf-8")
        source_form_fields = (self._project_root / "web/src/form-fields.js").read_text(
            encoding="utf-8"
        )
        if runtime_i18n != source_i18n:
            raise FrontendValidationError(
                "React and packaged runtime must share the exact same i18n implementation"
            )
        if runtime_form_fields != source_form_fields:
            raise FrontendValidationError(
                "React and packaged runtime must share the exact same "
                "form validation implementation"
            )
        self._validate_i18n_contract(runtime_js, runtime_i18n)
        if "Dashboard de pilotage OpenInfra" in payload:
            raise FrontendValidationError("runtime dashboard title must be shortened to Dashboard")
        if "renderOverviewRuntimeMetrics(displayedVersion, config, protectedForms)" not in payload:
            raise FrontendValidationError("runtime dashboard metrics must be scoped to overview")
        for fragment in (
            "Dashboard",
            "bg-dark text-white",
            "openinfra-sidebar",
            "openinfra-accordion",
            "Statistiques des composants OpenInfra",
            "openinfra-component-card",
            "openinfra-pie-chart",
            "padding-block: clamp(1rem, 2vw, 1.75rem)",
            "openinfra-titlebar h1",
            "--openinfra-pie-size: clamp(8rem, 14vw, 10.5rem)",
            "--openinfra-navy: #001b41",
            "--openinfra-action: #0066ff",
            "--openinfra-green: #15a362",
            "conic-gradient(var(--openinfra-action) 0 var(--oi-read-end), var(--openinfra-green)",
            "background: var(--openinfra-action);",
            "background: var(--openinfra-green);",
            "--openinfra-content-shadow: 0 .16rem .55rem rgba(0, 27, 65, .055)",
            "--openinfra-content-shadow-hover: 0 .28rem .8rem rgba(0, 27, 65, .07)",
            (
                "--openinfra-header-shadow: 0 .5rem 1.25rem rgba(0, 27, 65, .11), "
                "0 .1rem .35rem rgba(0, 61, 143, .08)"
            ),
            ".openinfra-top-header.bg-dark",
            ".openinfra-header-stack",
            "position: fixed",
            "box-shadow: var(--openinfra-header-shadow)",
            "scroll-padding-top: var(--openinfra-fixed-header-height)",
            "width: 100%",
            "padding-top: var(--openinfra-fixed-header-height)",
            "top: var(--openinfra-fixed-header-height)",
            "--openinfra-fixed-header-height",
            "scrollbar-gutter: stable",
            "overscroll-behavior: contain",
            ".openinfra-accordion-panel.show",
            "grid-template-rows: 0fr",
            "grid-template-rows: 1fr",
            "openinfra-accordion-panel-inner",
            "openinfra-sidebar-context-panel",
            "openinfra-sidebar-context-panel-inner",
            "data-context-module-id",
            "toggleSidebarContext",
            "openedContexts",
            "prefers-reduced-motion",
            "openinfra-global-toolbar",
            "openinfra-component-nav",
            "openinfra-mega-menu",
            "openinfra-compact-menu-button",
            "openinfra-mobile-menu-icon",
            "openinfra-compact-navigation",
            "openinfra-navigation-backdrop",
            "openinfra-toolbar-actions",
            "isMegamenuViewport",
            "closeResponsiveNavigation",
            "openMegaMenu",
            "openinfra-component-link",
            "mouseenter",
            "openinfra-header-stack",
            "--openinfra-fixed-header-height",
            "openinfra-global-toolbar-inner",
            "openinfra-global-search",
            "openinfra-global-search-icon",
            "openinfra-global-search-results",
            "Recherche globale OpenInfra",
            "renderGlobalSearchToolbar",
            "renderGlobalSearchResults",
            "syncFixedHeaderOffset",
            "globalSearchGroups",
            "globalSearchUrl",
            "/v1/search/global",
            "globalSearchBackend",
            "Recherche backend temporairement indisponible",
            "data-search-operation-id",
            "data-search-route",
            "Swagger",
            "ReDoc",
            "apiDocumentation",
            "apiDocumentationLinks",
            "buildApiDocumentationUrl",
            "Ouvrir Swagger UI backend API",
            "Ouvrir ReDoc backend API",
            "openinfra-api-doc-actions",
            "openinfra-edition-badge",
            "Politiques éditions et quotas",
            "Vérifier une capacité édition",
            "Vérifier un quota édition",
            "Chunk export signé",
            "/v1/exports/artifact-chunk",
            "/v1/editions/policies",
            "/v1/editions/feature-check",
            "/v1/editions/quota-check",
            "distributed_discovery_agents",
            "discovery_collector",
            "requested_increment",
            "exportJobId",
            "chunkOffset",
            "chunkSize",
            "#2a0015 0%, #4b001f 46%, #6a1430 100%",
            ".badge.openinfra-edition-badge",
            "openinfra-skip-link",
            "Aller au contenu principal",
            "openinfra-main-content",
            'role="listbox"',
            'role="option"',
            "aria-current",
            "aria-live",
            "aria-autocomplete",
            "openinfra-live-region",
            "skipToNavigation",
            "skipToSearch",
            "componentNavigationInstructions",
            "ArrowRight",
            "ArrowLeft",
            "ArrowDown",
            "opensNewWindow",
            "focusMainContentIfRequested",
            "grid-template-columns: minmax(0, 1fr) minmax(0, 50%) minmax(0, 1fr)",
            "grid-template-columns: repeat(11, minmax(0, 1fr))",
            "@media (min-width: 768px) and (max-width: 1199.98px)",
            "@media (max-width: 767.98px)",
            "@media (pointer: coarse)",
            "--openinfra-toolbar-control-height: 2rem",
            "--openinfra-toolbar-control-height: 2.75rem",
            "padding-block: .5rem !important",
            ".btn-primary",
            ".form-control:focus",
            'fetch("/status"',
            "Formulaires protégés",
            "openinfra-runtime-status",
            "#003D8F",
            "#24d8ab",
            "/v1/integrations/itsm/providers",
            "/v1/integrations/itsm/servicenow/validate",
            "/v1/integrations/itsm/servicenow/ci-sync-plan",
            "/v1/integrations/itsm/jira/validate",
            "/v1/integrations/itsm/jira/asset-sync-plan",
            "ServiceNow",
            "Jira Service Management",
            "Valider connecteur Jira Assets",
            "/v1/ipam/ui-search",
            "idempotency_key",
            "endpoint_url",
            "requested_scope",
            "RSOT (Ressource Source of Truth)",
            'icon: "reference"',
            "OPENINFRA_ICONS",
            "reference:",
            "asset:",
            (
                "M1 2a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2"
                "H3a2 2 0 0 1-2-2V2zm6.7 0a2 2 0 0 1 2-2h1.6a2 2 0 0 1 "
                "2 2v12a2 2 0 0 1-2 2H9.7a2 2 0 0 1-2-2V2zm6.25.55A1.8 "
                "1.8 0 0 1 15 4.18v7.64a1.8 1.8 0 0 1-1.05 1.63V2.55z"
            ),
            "IT Asset Management",
            "ITAM",
            'icon: "asset"',
            "/v1/itam/support-profile",
            "/v1/itam/support-coverage",
            "Déclarer garantie constructeur",
            "Ajouter support tiers",
            "OPENINFRA_MODULES.map((module)",
            "agents proxy collectors Enterprise uniquement",
            "Numéro de série",
            "/v1/rsot/reconcile-object",
            "Réconcilier une ressource",
            "Catalogue catégories / types",
            "RESOURCE_TAXONOMY",
            "RESOURCE_CATEGORY_OPTIONS",
            "Rack server",
            "optionLabel(option)",
            "optionValue(option)",
            "data-options-by-field",
            "resource_type",
            "Dashboard IPAM",
            "/v1/ipam/ui-dashboard",
            "Définir une VRF",
            "/v1/ipam/vrfs",
            "Définir un agrégat IP",
            "/v1/ipam/aggregates",
            "Définir un préfixe IP",
            "/v1/ipam/prefixes",
            "Définir une plage IP",
            "/v1/ipam/ranges",
            "Enregistrer une adresse IP",
            "/v1/ipam/addresses",
            "Assistant de réservation IP",
            "/v1/ipam/reservation-wizard",
            "Afficher les bindings réseau",
            "/v1/ipam/network-bindings",
            "Topologie opérationnelle IPAM",
            "/v1/ipam/topology",
            "Définir un groupe VLAN",
            "/v1/ipam/vlan-groups",
            "Définir un VXLAN VNI",
            "/v1/ipam/vxlan-vnis",
            "Définir un VLAN",
            "/v1/ipam/vlans",
            "Définir un ASN",
            "/v1/ipam/asns",
            "Définir un peer BGP",
            "/v1/ipam/bgp-peers",
            "Observer un enregistrement DNS",
            "/v1/ipam/dns-observations",
            "Observer un bail DHCP",
            "/v1/ipam/dhcp-leases",
            "Prévisualiser DDI",
            "/v1/ipam/ddi-preview",
            "RT import",
            "Fournisseurs DDI",
            "Inventaire PKI",
            "/v1/certificates/import",
            "/v1/certificates/get",
            "/v1/certificates/endpoints/observe",
            "/v1/certificates/assessment",
            "Chaîne PEM",
            "Route distinguisher",
            "Usage plage",
            "Localiser un équipement",
            "/v1/dcim/locations",
            "Élévation rack",
            "/v1/dcim/rack-elevation",
            "Définir un panneau de brassage",
            "/v1/dcim/patch-panels",
            "Définir un port DCIM",
            "/v1/dcim/ports",
            "Connecter un câble",
            "/v1/dcim/cables",
            "Définir un équipement électrique",
            "/v1/dcim/power-devices",
            "Définir un circuit électrique",
            "/v1/dcim/power-circuits",
            "Définir une zone de refroidissement",
            "/v1/dcim/cooling-zones",
            "Réserver la puissance équipement",
            "/v1/dcim/power-reservations",
            "Capacité énergie/refroidissement",
            "/v1/dcim/energy-cooling-capacity",
            "Jumeau numérique salle",
            "/v1/dcim/digital-twin",
            "Chaîne électrique",
            "Capacité watts",
            "Capacité froid watts",
            "Chemin câble",
            "Média câble",
            "Format rendu",
            "Face rack",
        ):
            if fragment not in payload:
                raise FrontendValidationError(
                    "runtime web assets do not expose the Bootstrap dashboard contract"
                )
        css_payload = assets_by_name["assets/openinfra-web.css"]
        if ".openinfra-sidebar {\n  width: 100%;" in css_payload:
            raise FrontendValidationError(
                "runtime web CSS must not force the desktop sidebar to full width"
            )
        forbidden = ("OPENINFRA_DATABASE_DSN", "postgresql://", "bind_password", "client_key")
        leaked = [fragment for fragment in forbidden if fragment in payload]
        if leaked:
            raise FrontendValidationError("runtime web assets leak forbidden backend data")
        for forbidden_ui in (
            "conic-gradient(var(--openinfra-navy) 0 var(--oi-read-end), var(--openinfra-fuchsia)",
            "background: var(--openinfra-fuchsia);",
            "max-height: 34rem",
            "transition: max-height",
            "OPENINFRA_MODULES.slice(0, 6)",
            "Token API",
            "physical-server",
            (
                'id: "rsot", label: "RSOT (Ressource Source of Truth)", '
                'shortLabel: "RSOT", icon: "table"'
            ),
            "openinfra-method",
            "Search OpenInfra operations",
            "openinfra-search",
            "openinfra-login",
            "openinfra-signup",
            'config?.authMode || "standard")}</span>',
            "config.authMode || 'standard'",
            "badge text-bg-primary openinfra-edition-badge",
            "var(--openinfra-fuchsia), #c900ff 48%, var(--openinfra-action)",
            "var(--openinfra-fuchsia) 0%, #ff2bd6 52%, #c000a8 100%",
            "#ff2bd6 52%, #c000a8",
            "#a52a2a",
            "Sign-up",
            "background: linear-gradient(135deg, rgba(0, 174, 239, .08)",
            "border: 1px solid rgba(0, 174, 239, .18)",
            "padding: .7rem .8rem !important",
            "openinfra-submit-btn",
            "Formulaire métier typé : chaque champ correspond",
            "Aucun champ générique Attributs",
        ):
            if forbidden_ui in payload:
                raise FrontendValidationError(
                    "runtime web assets expose a forbidden generic/technical UI fragment: "
                    + forbidden_ui
                )
        forbidden_reference_outline = (
            "M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2"
            "a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 "
            "1 0 0 0 1-1V2a1 1 0 0 0-1-1H3zm3 7V2h1v5.117"
        )
        if forbidden_reference_outline in payload:
            raise FrontendValidationError("RSOT reference icon must use the filled opaque variant")
        for forbidden_alert in (
            "alert alert-info",
            'role="note"',
            '<div class="alert alert-info" role="note">',
        ):
            if forbidden_alert in runtime_js:
                raise FrontendValidationError(
                    "runtime web assets render a default informational alert: " + forbidden_alert
                )
        success_condition = (
            '${result && activeModuleId !== "overview" ? `<div class="alert alert-success"'
        )
        if success_condition not in runtime_js:
            raise FrontendValidationError(
                "runtime web assets must keep success alerts conditional on form submissions"
            )
        return required


class FrontendValidationCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Validate OpenInfra P08 frontend contract")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        args = parser.parse_args()
        try:
            report = FrontendContractValidator(args.project_root).validate()
        except (FrontendValidationError, json.JSONDecodeError) as exc:
            sys.stderr.write(str(exc) + "\n")
            return 1
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(FrontendValidationCli.main())
