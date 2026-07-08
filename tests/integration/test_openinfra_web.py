from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from openinfra import __version__
from openinfra.domain.common import OpenInfraError
from openinfra.interfaces.web import (
    OpenInfraWebConfig,
    OpenInfraWebConfigValidator,
    OpenInfraWebServer,
    OpenInfraWebStaticLocator,
)


def _test_server_side_bearer() -> str:
    return "-".join(("server", "side", "secret"))


def _test_browser_bearer() -> str:
    return "-".join(("browser", "token"))


class BackendFakeHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return None

    def do_GET(self) -> None:
        if self.path == "/ready":
            self._json(HTTPStatus.OK, {"ready": True, "backend": "fake"})
            return
        if self.path == "/api/v1/version":
            self._json(HTTPStatus.OK, {"version": __version__})
            return
        if self.path in {"/docs", "/swagger"}:
            body = b"<html><body>SwaggerUIBundle backend API</body></html>"
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/redoc":
            body = b"<html><body>redoc.standalone.js backend API</body></html>"
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in {"/openapi.yaml", "/api/v1/openapi.yaml"}:
            body = b"openapi: 3.1.0\ninfo:\n  title: OpenInfra\n"
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "application/yaml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": self.path})

    def do_POST(self) -> None:
        if self.path == "/api/v1/echo":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self._json(
                HTTPStatus.CREATED,
                {
                    "received": payload,
                    "authorization": self.headers.get("Authorization", ""),
                    "browser_authorization_forwarded": self.headers.get("Authorization")
                    == "Bearer browser-token",
                    "web_trust": self.headers.get("X-OpenInfra-Web-Trust"),
                },
            )
            return
        if self.path == "/api/v1/raw-missing-bearer":
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "missing bearer token"})
            return
        if self.path == "/api/v1/plain-unauthorized":
            body = b"not-json"
            self.send_response(HTTPStatus.UNAUTHORIZED.value)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/v1/array-unauthorized":
            body = b"[]"
            self.send_response(HTTPStatus.UNAUTHORIZED.value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": self.path})

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class RunningServer:
    def __init__(self, server: ThreadingHTTPServer) -> None:
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self) -> RunningServer:
        self.thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class TestOpenInfraWeb:
    def test_web_serves_assets_config_readiness_and_api_proxy(self) -> None:
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            config = self._config(backend.base_url, backend_bearer_token=_test_server_side_bearer())
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                index = self._get_text(web.base_url + "/")
                bootstrap_css = self._get_text(web.base_url + "/assets/bootstrap.min.css")
                static_css = self._get_text(web.base_url + "/assets/openinfra-web.css")
                static_js = self._get_text(web.base_url + "/assets/openinfra-web.js")
                main_js = Path("web/src/main.jsx").read_text(encoding="utf-8")
                public_config = self._get_json(web.base_url + "/config.json")
                bff_status = self._get_json(web.base_url + "/status")
                readiness = self._get_json(web.base_url + "/ready")
                version = self._get_json(web.base_url + "/api/v1/version")
                web_version = self._get_json(web.base_url + "/version")
                swagger = self._get_text(web.base_url + "/docs")
                swagger_alias = self._get_text(web.base_url + "/swagger")
                redoc = self._get_text(web.base_url + "/redoc")
                openapi = self._get_text(web.base_url + "/openapi.yaml")
                versioned_openapi = self._get_text(web.base_url + "/api/v1/openapi.yaml")
                echoed = self._post_json(
                    web.base_url + "/api/v1/echo",
                    {"tenant_id": "default", "value": 42},
                    browser_bearer=_test_browser_bearer(),
                )

        assert "openinfra-root" in index
        assert "/assets/bootstrap.min.css" in index
        assert "Bootstrap" in bootstrap_css and "v5." in bootstrap_css
        assert "openinfra-sidebar" in static_css
        assert "OpenInfraDashboard" in static_js
        assert "Dashboard de pilotage OpenInfra" not in static_js
        assert 'const pageTitle = activeModuleId === "overview" ? "Dashboard"' in static_js
        assert "renderOverviewRuntimeMetrics" in static_js
        assert "activeModuleId === 'overview' &&" in main_js
        assert "Search OpenInfra operations" not in static_js
        assert "openinfra-login" not in static_js and "openinfra-signup" not in static_js
        assert "Login" not in static_js and "Sign-up" not in static_js
        assert "openinfra-global-toolbar" in static_js + static_css
        assert "openinfra-global-search" in static_js + static_css
        assert "Recherche globale OpenInfra" in static_js
        assert "openinfra-global-search-icon" in static_js + static_css
        assert "openinfra-global-search-results" in static_js + static_css
        assert "renderGlobalSearchToolbar" in static_js
        assert "renderGlobalSearchResults" in static_js
        assert "globalSearchGroups" in static_js + main_js
        assert "buildGlobalSearchUrl" in main_js
        assert "globalSearchUrl" in static_js
        assert "Recherche backend temporairement indisponible" in static_js + main_js
        assert "Recherche backend indisponible" not in static_js + main_js
        assert "Résultats locaux ci-dessous" in static_js + main_js
        assert "data-search-operation-id" in static_js
        assert "Swagger" in static_js and "ReDoc" in static_js
        assert "apiDocumentation" in static_js + main_js
        assert "apiDocumentationLinks" in static_js + main_js
        assert "buildApiDocumentationUrl" in static_js + main_js
        assert "Ouvrir Swagger UI backend API" in static_js + main_js
        assert "Ouvrir ReDoc backend API" in static_js + main_js
        assert "openinfra-api-doc-actions" in static_js + static_css
        assert "openinfra-edition-badge" in static_js + static_css + main_js
        edition_badge_rule = static_css.split(".badge.openinfra-edition-badge", 1)[1].split("}", 1)[
            0
        ]
        assert "#2a0015 0%, #4b001f 46%, #6a1430 100%" in edition_badge_rule
        assert "#ff2bd6" not in edition_badge_rule
        assert "#c000a8" not in edition_badge_rule
        assert "var(--openinfra-fuchsia)" not in edition_badge_rule
        assert "#a52a2a" not in edition_badge_rule
        assert "brown" not in edition_badge_rule.lower()
        assert "badge text-bg-primary openinfra-edition-badge" not in static_js + main_js
        assert "var(--openinfra-action)) !important;" not in edition_badge_rule
        assert 'config?.edition || "runtime")}</span>' in static_js
        assert 'config?.authMode || "standard")}</span>' not in static_js
        assert "config.authMode || 'standard'" not in main_js
        assert "openinfra-skip-link" in static_js + static_css + main_js
        assert "Aller au contenu principal" in static_js + main_js
        assert "openinfra-main-content" in static_js + main_js
        assert "aria-current" in static_js + main_js
        assert 'role="listbox"' in static_js + main_js
        assert 'role="option"' in static_js + main_js
        assert "aria-live" in static_js + main_js
        assert "focusMainContentIfRequested" in static_js
        assert "shouldFocusMain" in main_js
        assert "aria-autocomplete" in static_js + main_js
        assert "aria-controls" in static_js + main_js
        assert "IT Asset Management" in static_js
        assert 'shortLabel: "ITAM"' in static_js
        assert 'icon: "asset"' in static_js
        assert "ITAM" in main_js
        assert "asset: '" in main_js
        assert "Entité propriétaire" in static_js + main_js
        assert 'label: "Tenant"' not in static_js
        assert '<label class="col-md-4 form-label">Tenant' not in static_js
        assert '<input id="openinfra-tenant"' not in static_js
        assert 'type: "tenant-select"' in static_js
        assert 'label: "Organisation"' in static_js
        assert 'label: "Entité propriétaire de sécurité", type: "tenant-select"' in static_js
        assert "Lister les entités propriétaires ITAM" in static_js + main_js
        assert "Créer une entité propriétaire ITAM" in static_js + main_js
        assert "Modifier une entité propriétaire ITAM" in static_js + main_js
        assert "Retirer une entité propriétaire ITAM" in static_js + main_js
        assert "/v1/itam/support-profile" in static_js + main_js
        assert "/v1/itam/support-coverage" in static_js + main_js
        assert "Déclarer garantie constructeur" in static_js + main_js
        assert "Ajouter support tiers" in static_js + main_js
        assert "Politiques éditions et quotas" in static_js + main_js
        assert "Vérifier une capacité édition" in static_js + main_js
        assert "Vérifier un quota édition" in static_js + main_js
        assert "/v1/editions/policies" in static_js + main_js
        assert "/v1/editions/feature-check" in static_js + main_js
        assert "/v1/editions/quota-check" in static_js + main_js
        assert "Imports / Exports" in static_js + main_js
        assert "Progression import massif" in static_js + main_js
        assert "/v1/imports/bulk-progress" in static_js + main_js
        assert "Guide migration données" in static_js + main_js
        assert "/v1/imports/migration-guide" in static_js + main_js
        assert "Chunk export signé" in static_js + main_js
        assert "/v1/exports/artifact-chunk" in static_js + main_js
        assert "FIELD_SETS.jobId" in static_js
        assert "FIELD_SETS.exportJobId" in static_js
        assert "FIELD_SETS.chunkOffset" in static_js
        assert "FIELD_SETS.chunkSize" in static_js
        assert "Plan discovery locale Lite/Pro" in static_js + main_js
        assert "/v1/discovery/local-plan" in static_js + main_js
        assert "Plan bootstrap agent Enterprise" in static_js + main_js
        assert "/v1/discovery/agent-bootstrap-plan" in static_js + main_js
        assert "no_rsot_write" not in static_js
        assert "distributed_discovery_agents" in static_js
        assert "discovery_collector" in static_js
        assert "requested_increment" in static_js
        assert "OPENINFRA_MODULES.map((module)" in static_js
        assert "OPENINFRA_MODULES.slice(0, 6)" not in static_js
        assert "MODULES.map((module)" in main_js
        assert "MODULES.slice(0, 6)" not in main_js
        assert "--bs-btn-padding-y: .22rem" in static_css
        assert "--bs-btn-padding-x: .5rem" in static_css
        assert "font-size: .72rem" in static_css
        assert "min-width: 2.875rem" in static_css
        assert (
            "grid-template-columns: minmax(0, 1fr) minmax(18rem, 50%) minmax(0, 1fr)" in static_css
        )
        assert "RSOT (Ressource Source of Truth)" in static_js
        assert 'icon: "reference"' in static_js
        assert "icon: 'reference'" in main_js
        assert "RSOT" in static_js
        assert (
            "M1 2a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2zm6.7 0a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9.7a2 2 0 0 1-2-2V2zm6.25.55A1.8 1.8 0 0 1 15 4.18v7.64a1.8 1.8 0 0 1-1.05 1.63V2.55z"
            in static_js
        )
        assert (
            "M1 2a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2zm6.7 0a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9.7a2 2 0 0 1-2-2V2zm6.25.55A1.8 1.8 0 0 1 15 4.18v7.64a1.8 1.8 0 0 1-1.05 1.63V2.55z"
            in main_js
        )
        assert (
            "M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3zm3 7V2h1v5.117"
            not in static_js + main_js
        )
        assert (
            'id: "rsot", label: "RSOT (Ressource Source of Truth)", shortLabel: "RSOT", icon: "table"'
            not in static_js
        )
        assert "bookmark" not in static_js.lower()  # icon remains inline SVG path data only
        assert "/v1/rsot/objects" in static_js
        assert "Backend prêt" not in static_js
        assert "alert alert-info" not in static_js
        assert 'role="note"' not in static_js
        assert '<div class="alert alert-info"' not in static_js
        assert "alert alert-info" not in main_js
        assert 'role="note"' not in main_js
        assert "Formulaire métier typé : chaque champ correspond" not in static_js
        assert "Formulaire métier typé : chaque champ correspond" not in main_js
        assert "Aucun champ générique Attributs" not in static_js
        assert "Aucun champ générique Attributs" not in main_js
        success_condition = (
            'result && activeModuleId !== "overview" ? `<div class="alert alert-success"'
        )
        assert success_condition in static_js
        assert "submissionCompleted && activeModuleId !== 'overview' &&" in main_js
        assert "Soumission exécutée avec succès" in static_js
        assert "OPENINFRA_SIDEBAR_CONTEXTS" in static_js
        assert "SIDEBAR_CONTEXTS" in main_js
        assert "sidebarOperationGroups" in static_js + main_js
        assert "renderSidebarOperationGroup" in static_js
        assert "openinfra-sidebar-context" in static_js + static_css + main_js
        assert "openinfra-sidebar-context-title" in static_js + static_css + main_js
        for context_label in (
            "Référentiel",
            "Relations & historique",
            "Qualité & gouvernance",
            "Vue & recherche",
            "Adressage IP",
            "Réseau L2/L3",
            "Observations & DDI",
            "Localisation & capacité",
            "Sites & dépendances",
            "Connectivité",
            "Énergie & refroidissement",
            "Jumeau numérique",
            "Support matériel",
            "Licences logicielles",
            "Locale Lite/Pro",
            "Agents Enterprise",
            "Imports",
            "Migration",
            "Exports",
            "Gouvernance ITSM",
            "ServiceNow",
            "Jira Assets",
            "GLPI Inventory",
            "Freshservice Assets",
            "Éditions & quotas",
            "Identité & accès",
            "Audit",
        ):
            assert context_label in static_js + main_js
        assert (
            '{ label: "ServiceNow", operationIds: ["servicenow-validate", "servicenow-ci-sync-plan"] }'
            in static_js
        )
        assert "group.operationIds.map((id) => byId.get(id)).filter(Boolean)" in static_js
        assert 'groups.push({ label: "Autres", operations: remaining })' in static_js
        assert "openinfra-accordion" in static_js + static_css
        assert ".openinfra-accordion-panel.show" in static_css
        assert "grid-template-rows: 0fr" in static_css
        assert "grid-template-rows: 1fr" in static_css
        assert "openinfra-accordion-panel-inner" in static_js + static_css + main_js
        assert "openinfra-sidebar-context-panel" in static_js + static_css + main_js
        assert "openinfra-sidebar-context-panel-inner" in static_js + static_css + main_js
        assert "data-context-module-id" in static_js
        assert "toggleSidebarContext" in static_js + main_js
        assert "openedContexts" in static_js + main_js
        assert "prefers-reduced-motion" in static_css
        assert "scrollbar-gutter: stable" in static_css
        assert "overscroll-behavior: contain" in static_css
        assert "max-height: 34rem" not in static_css
        assert "transition: max-height" not in static_css
        assert "Statistiques des composants OpenInfra" in static_js
        assert "Accueil — statistiques des composants" in static_js
        assert "openinfra-component-card" in static_js + static_css
        assert "openinfra-pie-chart" in static_js + static_css
        assert "padding-block: clamp(1rem, 2vw, 1.75rem)" in static_css
        assert "openinfra-titlebar h1" in static_css
        assert "--openinfra-pie-size: clamp(8rem, 14vw, 10.5rem)" in static_css
        assert "Formulaires protégés" in static_js
        assert 'fetch("/status"' in static_js
        assert "@media (max-width: 575.98px)" in static_css
        assert "v0.29.65: responsive sidebar" in static_css
        assert "v0.29.66: extra-small mobile sidebar" in static_css
        assert "openinfra-mobile-menu-button" in static_js + static_css + main_js
        assert "openinfra-mobile-menu-icon" in static_js + static_css + main_js
        assert "openinfra-mobile-sidebar-backdrop" in static_js + static_css + main_js
        assert 'aria-controls="openinfra-sidebar"' in static_js + main_js
        assert "mobileSidebarOpen" in static_js + main_js
        assert "shouldCloseMobileSidebar" in static_js
        assert 'matchMedia("(max-width: 575.98px)")' in static_js
        assert "mobile-open" in static_js + static_css + main_js
        assert "M2 4h12v1.4H2V4zm0 3.3h12v1.4H2V7.3zm0 3.3h12V12H2v-1.4z" in static_js + main_js
        assert not re.search(r"\.openinfra-sidebar\s*\{[^}]*width:\s*100%", static_css)
        assert "@media (max-width: 991.98px)" in static_css
        assert "@media (max-width: 767.98px)" in static_css
        assert "max-height: min(42vh, 26rem)" in static_css
        assert "--openinfra-navy: #001b41" in static_css
        assert "--openinfra-action: #0066ff" in static_css
        assert "--openinfra-green: #15a362" in static_css
        assert (
            "conic-gradient(var(--openinfra-action) 0 var(--oi-read-end), var(--openinfra-green)"
            in static_css
        )
        assert "background: var(--openinfra-action);" in static_css
        assert "background: var(--openinfra-green);" in static_css
        assert (
            "conic-gradient(var(--openinfra-navy) 0 var(--oi-read-end), var(--openinfra-fuchsia)"
            not in static_css
        )
        assert "background: var(--openinfra-fuchsia);" not in static_css
        assert ".openinfra-edition-badge" in static_css
        assert ".badge.openinfra-edition-badge" in static_css
        assert "--openinfra-content-shadow: 0 .16rem .55rem rgba(0, 27, 65, .055)" in static_css
        assert "--openinfra-content-shadow-hover: 0 .28rem .8rem rgba(0, 27, 65, .07)" in static_css
        assert (
            "--openinfra-header-shadow: 0 .95rem 2.25rem rgba(0, 27, 65, .18), 0 .16rem .55rem rgba(0, 61, 143, .16)"
            in static_css
        )
        assert "box-shadow: var(--openinfra-content-shadow);" in static_css
        assert "box-shadow: var(--openinfra-content-shadow-hover);" in static_css
        assert "box-shadow: var(--openinfra-header-shadow);" in static_css
        assert ".openinfra-top-header.bg-dark" in static_css
        assert ".openinfra-header-stack" in static_css
        assert "position: fixed" in static_css
        assert "scroll-padding-top: var(--openinfra-fixed-header-height)" in static_css
        assert "width: 100%" in static_css
        assert "padding-top: var(--openinfra-fixed-header-height)" in static_css
        assert "top: var(--openinfra-fixed-header-height)" in static_css
        assert "--openinfra-fixed-header-height" in static_css
        assert "openinfra-header-stack" in static_js + main_js
        assert "syncFixedHeaderOffset" in static_js
        assert "syncHeaderOffset" in main_js
        assert ".btn-primary" in static_css
        assert "--bs-btn-bg: #24d8ab" in static_css
        assert "--bs-btn-focus-shadow-rgb: 36, 216, 171" in static_css
        assert "openinfra-submit-btn" not in static_js + main_js + static_css
        assert "color: #003D8F !important" in static_css
        assert "background: linear-gradient(135deg, rgba(0, 174, 239, .08)" not in static_css
        assert "border: 1px solid rgba(0, 174, 239, .18)" not in static_css
        assert ".form-control:focus" in static_css
        assert "#0d6efd" not in static_css
        assert "Camembert" in static_js
        assert 'path: "/v1/integrations/itsm/providers"' in static_js
        assert 'path: "/v1/integrations/itsm/servicenow/validate"' in static_js
        assert 'path: "/v1/integrations/itsm/servicenow/ci-sync-plan"' in static_js
        assert 'path: "/v1/integrations/itsm/jira/validate"' in static_js
        assert 'path: "/v1/integrations/itsm/jira/asset-sync-plan"' in static_js
        assert 'path: "/v1/integrations/itsm/glpi/validate"' in static_js
        assert 'path: "/v1/integrations/itsm/glpi/asset-sync-plan"' in static_js
        assert 'path: "/v1/integrations/itsm/freshservice/validate"' in static_js
        assert 'path: "/v1/integrations/itsm/freshservice/asset-sync-plan"' in static_js
        assert "OpenService" not in static_js
        assert "/v1/integrations/itsm/openservice" not in static_js
        assert "Valider connecteur ServiceNow" in static_js
        assert "Valider connecteur Jira Assets" in static_js
        assert "Valider connecteur GLPI Inventory" in static_js
        assert "Valider connecteur Freshservice Assets" in static_js
        assert 'path: "/v1/ipam/ui-search"' in static_js
        assert "idempotency_key" in static_js
        assert "endpoint_url" in static_js
        assert "requested_scope" in static_js
        assert 'path: "/api/v1/database/schema"' not in static_js
        assert "Numéro de série" in static_js
        assert 'path: "/v1/rsot/reconcile-object"' in static_js
        assert "Réconcilier une ressource" in static_js
        assert "Catalogue catégories / types" in static_js
        assert "RESOURCE_TAXONOMY" in static_js
        assert "physical-server" not in static_js
        assert "Rack server" in static_js and "Firewall" in static_js
        assert '"value": "rack-server"' in static_js
        assert '"label": "Rack server"' in static_js
        assert "optionLabel(option)" in static_js
        assert "optionValue(option)" in static_js
        assert "data-options-by-field" in static_js
        assert "resource_type" in static_js
        assert "Token API" not in static_js
        assert "openinfra-method" not in static_js + static_css
        assert "agents proxy collectors Enterprise uniquement" in static_js
        assert 'path: "/v1/ipam/ui-dashboard"' in static_js
        assert "Dashboard IPAM" in static_js
        assert 'path: "/v1/ipam/vrfs"' in static_js
        assert "Définir une VRF" in static_js
        assert 'path: "/v1/ipam/aggregates"' in static_js
        assert "Définir un agrégat IP" in static_js
        assert 'path: "/v1/ipam/prefixes"' in static_js
        assert "Définir un préfixe IP" in static_js
        assert 'path: "/v1/ipam/ranges"' in static_js
        assert "Définir une plage IP" in static_js
        assert 'path: "/v1/ipam/addresses"' in static_js
        assert "Enregistrer une adresse IP" in static_js
        assert 'path: "/v1/ipam/reservation-wizard"' in static_js
        assert "Assistant de réservation IP" in static_js
        assert 'path: "/v1/ipam/network-bindings"' in static_js
        assert "Afficher les bindings réseau" in static_js
        assert 'path: "/v1/ipam/topology"' in static_js
        assert "Topologie opérationnelle IPAM" in static_js
        assert 'path: "/v1/ipam/vlan-groups"' in static_js
        assert "Définir un groupe VLAN" in static_js
        assert 'path: "/v1/ipam/vxlan-vnis"' in static_js
        assert "Définir un VXLAN VNI" in static_js
        assert 'path: "/v1/ipam/vlans"' in static_js
        assert "Définir un VLAN" in static_js
        assert 'path: "/v1/ipam/asns"' in static_js
        assert "Définir un ASN" in static_js
        assert 'path: "/v1/ipam/bgp-peers"' in static_js
        assert "Définir un peer BGP" in static_js
        assert 'path: "/v1/ipam/dns-observations"' in static_js
        assert "Observer un enregistrement DNS" in static_js
        assert 'path: "/v1/ipam/dhcp-leases"' in static_js
        assert "Observer un bail DHCP" in static_js
        assert 'path: "/v1/ipam/ddi-preview"' in static_js
        assert "Prévisualiser DDI" in static_js
        assert "RT import" in static_js
        assert "Fournisseurs DDI" in static_js
        assert 'path: "/v1/dcim/locations"' in static_js
        assert "Localiser un équipement" in static_js
        assert 'path: "/v1/dcim/rack-elevation"' in static_js
        assert "Élévation rack" in static_js
        assert "Format rendu" in static_js
        assert "Face rack" in static_js
        assert "Position U" in static_js
        assert 'path: "/v1/dcim/patch-panels"' in static_js
        assert "Définir un panneau de brassage" in static_js
        assert 'path: "/v1/dcim/ports"' in static_js
        assert "Définir un port DCIM" in static_js
        assert 'path: "/v1/dcim/cables"' in static_js
        assert "Connecter un câble" in static_js
        assert "Chemin câble" in static_js
        assert "Média câble" in static_js
        assert 'path: "/v1/dcim/power-devices"' in static_js
        assert "Définir un équipement électrique" in static_js
        assert 'path: "/v1/dcim/power-circuits"' in static_js
        assert "Définir un circuit électrique" in static_js
        assert 'path: "/v1/dcim/cooling-zones"' in static_js
        assert "Définir une zone de refroidissement" in static_js
        assert 'path: "/v1/dcim/power-reservations"' in static_js
        assert "Réserver la puissance équipement" in static_js
        assert 'path: "/v1/dcim/energy-cooling-capacity"' in static_js
        assert "Capacité énergie/refroidissement" in static_js
        assert 'path: "/v1/dcim/digital-twin"' in static_js
        assert "Jumeau numérique salle" in static_js
        assert "Chaîne électrique" in static_js
        assert 'path: "/v1/dcim/sites"' in static_js + main_js
        assert 'path: "/v1/dcim/site/create"' in static_js + main_js
        assert 'path: "/v1/dcim/site/update"' in static_js + main_js
        assert 'path: "/v1/dcim/site/delete"' in static_js + main_js
        assert 'path: "/v1/dcim/topology-catalog"' in static_js + main_js
        assert "Lister les sites DCIM" in static_js + main_js
        assert "Créer un site DCIM" in static_js + main_js
        assert "Catalogue dépendances DCIM" in static_js + main_js
        assert "DCIM_REFERENCE_FIELDS" in static_js
        assert "isDcimReferenceField(field)" in static_js
        assert "async refreshDcimCatalog()" in static_js
        assert "dcimReferenceLevel(field)" in static_js
        assert "dcimOptions(field)" in static_js
        assert "isDcimReferenceField(field)" in static_js
        assert "DCIM topology catalog returned" in static_js
        assert 'this.state.selected.id.startsWith("dcim-")' in static_js
        toggle_body = static_js.split("toggleAccordion(moduleId)", 1)[1].split("toggleSidebarContext", 1)[0]
        assert "activeModuleId: module.id" not in toggle_body
        assert "selected: module.operations[0]" not in toggle_body
        assert "dcimCatalog" in static_js
        assert "data-field" in static_js
        assert (
            'type="text"'
            not in static_js.split("isDcimReferenceField(field)", 1)[1].split(
                'if (field.type === "select")', 1
            )[0]
        )
        assert 'path: "/v1/itam/support-profile"' in static_js
        assert "Profil support actif" in static_js
        assert 'path: "/v1/itam/support-coverage"' in static_js
        assert "Couverture support actif" in static_js
        assert "Capacité froid watts" in static_js
        assert "postgresql://" not in index + static_js + static_css
        assert "OPENINFRA_DATABASE_DSN" not in index + static_js + static_css
        assert public_config == {
            "apiBaseUrl": "/api",
            "apiDocumentation": {
                "openapiUrl": "/openapi.yaml",
                "redocUrl": "/redoc",
                "swaggerAliasUrl": "/swagger",
                "swaggerUrl": "/docs",
                "versionedOpenapiUrl": "/api/v1/openapi.yaml",
            },
            "authMode": "standard",
            "backendProxy": "/api",
            "databaseTrust": "not-configured",
            "edition": "pro",
            "service": "openinfra-web",
            "version": __version__,
            "webBackendTrust": "server-side",
        }
        assert "SwaggerUIBundle backend API" in swagger
        assert "SwaggerUIBundle backend API" in swagger_alias
        assert "redoc.standalone.js backend API" in redoc
        assert readiness["ready"] is True
        assert bff_status["protectedForms"] == "enabled"
        assert bff_status["trust"]["backendBearer"] == "configured"
        assert "server-side-secret" not in json.dumps(bff_status, sort_keys=True)
        assert version["version"] == __version__
        assert web_version["version"] == __version__
        assert "openapi: 3.1.0" in openapi
        assert versioned_openapi == openapi
        assert echoed == {
            "authorization": "Bearer server-side-secret",
            "browser_authorization_forwarded": False,
            "received": {"tenant_id": "default", "value": 42},
            "web_trust": "server-side",
        }

    def test_dashboard_form_operation_paths_are_real_backend_contracts(self) -> None:
        static_js = Path(
            "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js"
        ).read_text(encoding="utf-8")
        api_source = Path("src/openinfra/interfaces/http_api.py").read_text(encoding="utf-8")
        operation_paths = sorted(set(re.findall(r'path: "([^"]+)"', static_js)))
        api_routes = set(re.findall(r'"(/api/v1/[^"]+)"', api_source))

        assert operation_paths
        assert "/v1/ipam/search" not in operation_paths
        assert "/api/v1/database/schema" not in operation_paths
        for operation_path in operation_paths:
            assert operation_path.startswith("/v1/")
            backend_route = "/api" + operation_path
            if backend_route in api_routes:
                continue
            if backend_route.startswith("/api/v1/rsot/"):
                legacy_route = "/api/v1/rsot/" + backend_route.removeprefix("/api/v1/rsot/")
                assert legacy_route in api_routes
                continue
            raise AssertionError("dashboard operation route is not backed by API: " + backend_route)

    def test_web_rejects_path_traversal_and_invalid_backend_configuration(self) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        with (
            RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend,
            RunningServer(
                OpenInfraWebServer(("127.0.0.1", 0), self._config(backend.base_url))
            ) as web,
            pytest.raises(urllib.error.HTTPError) as exc,
        ):
            self._get_json(web.base_url + "/../pyproject.toml")

        assert exc.value.code == HTTPStatus.NOT_FOUND.value
        with pytest.raises(OpenInfraError):
            OpenInfraWebConfigValidator().validate(
                OpenInfraWebConfig(
                    host="127.0.0.1",
                    port=2006,
                    backend_url="http://user:pass@example.net",
                    public_api_base_url="/api",
                    public_api_docs_base_url="",
                    static_root=static_root,
                    edition="pro",
                    auth_mode="standard",
                    allow_insecure_backend=True,
                )
            )
        with pytest.raises(OpenInfraError):
            OpenInfraWebConfigValidator().validate(
                OpenInfraWebConfig(
                    host="127.0.0.1",
                    port=2006,
                    backend_url="http://backend.internal",
                    public_api_base_url="/api",
                    public_api_docs_base_url="",
                    static_root=static_root,
                    edition="enterprise",
                    auth_mode="standard",
                    allow_insecure_backend=False,
                )
            )
        with pytest.raises(OpenInfraError):
            OpenInfraWebConfigValidator().validate(
                OpenInfraWebConfig(
                    host="127.0.0.1",
                    port=2006,
                    backend_url="http://backend.internal",
                    public_api_base_url="/api",
                    public_api_docs_base_url="https://user:pass@example.net/docs",
                    static_root=static_root,
                    edition="pro",
                    auth_mode="standard",
                    allow_insecure_backend=True,
                )
            )

    def test_public_api_documentation_roots_and_docs_url_validation(self) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        explicit_docs = OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url="https://backend.example.net",
            public_api_base_url="/api",
            public_api_docs_base_url="https://docs.example.net",
            static_root=static_root,
            edition="enterprise",
            auth_mode="standard",
            allow_insecure_backend=False,
        )
        origin_docs = OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url="https://backend.example.net",
            public_api_base_url="https://api.example.net/api",
            public_api_docs_base_url="",
            static_root=static_root,
            edition="enterprise",
            auth_mode="standard",
            allow_insecure_backend=False,
        )

        assert (
            explicit_docs.api_documentation_links()["swaggerUrl"] == "https://docs.example.net/docs"
        )
        assert origin_docs.api_documentation_links()["redocUrl"] == "https://api.example.net/redoc"

        validator = OpenInfraWebConfigValidator()
        for public_docs_url in (
            "ftp://docs.example.net",
            "https://user:secret@docs.example.net",
            "https://docs.example.net?debug=true",
        ):
            with pytest.raises(OpenInfraError):
                validator.validate(
                    OpenInfraWebConfig(
                        host="127.0.0.1",
                        port=0,
                        backend_url="https://backend.example.net",
                        public_api_base_url="/api",
                        public_api_docs_base_url=public_docs_url,
                        static_root=static_root,
                        edition="enterprise",
                        auth_mode="standard",
                        allow_insecure_backend=False,
                    )
                )

    def test_web_injects_server_side_backend_bearer_token_without_exposing_it(self) -> None:
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            config = self._config(backend.base_url, backend_bearer_token=_test_server_side_bearer())
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                static_js = self._get_text(web.base_url + "/assets/openinfra-web.js")
                main_js = Path("web/src/main.jsx").read_text(encoding="utf-8")
                public_config = self._get_json(web.base_url + "/config.json")
                echoed = self._post_json(
                    web.base_url + "/api/v1/echo",
                    {"tenant_id": "default", "value": 99},
                )

        assert "server-side-secret" not in static_js + json.dumps(public_config, sort_keys=True)
        assert echoed["authorization"] == "Bearer server-side-secret"
        assert echoed["browser_authorization_forwarded"] is False
        assert echoed["web_trust"] == "server-side"

    def test_config_factory_falls_back_to_bootstrap_token_when_web_token_is_blank(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        monkeypatch.setenv("OPENINFRA_WEB_BACKEND_BEARER_TOKEN", "   ")
        monkeypatch.setenv("OPENINFRA_BOOTSTRAP_TOKEN", "bootstrap-runtime-token")
        factory = __import__(
            "openinfra.interfaces.web", fromlist=["OpenInfraWebConfigFactory"]
        ).OpenInfraWebConfigFactory()

        config = factory.from_args(
            [
                "--backend-url",
                "http://backend.internal",
                "--static-root",
                str(static_root),
                "--edition",
                "pro",
                "--allow-insecure-backend",
            ]
        )

        assert config.backend_bearer_token == "bootstrap-runtime-token"

    def test_protected_web_proxy_never_returns_raw_missing_bearer_token(self) -> None:
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            config = self._config(backend.base_url)
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                status = self._get_json(web.base_url + "/status")
                with pytest.raises(urllib.error.HTTPError) as exc:
                    self._post_json(web.base_url + "/api/v1/echo", {"tenant_id": "default"})
                payload = json.loads(exc.value.read().decode("utf-8"))

        assert status["protectedForms"] == "blocked-by-missing-server-bearer"
        assert status["trust"]["backendBearer"] == "not-configured"
        assert "OPENINFRA_BOOTSTRAP_TOKEN" in status["remediation"]["environment"]
        assert exc.value.code == HTTPStatus.SERVICE_UNAVAILABLE.value
        assert payload["error"] == "web backend bearer token is not configured"
        assert "missing bearer token" not in json.dumps(payload)

    def test_web_proxy_sanitizes_backend_raw_missing_bearer_response(self) -> None:
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            config = self._config(backend.base_url, backend_bearer_token=_test_server_side_bearer())
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                with pytest.raises(urllib.error.HTTPError) as exc:
                    self._post_json(web.base_url + "/api/v1/raw-missing-bearer", {})
                payload = json.loads(exc.value.read().decode("utf-8"))
                with pytest.raises(urllib.error.HTTPError) as plain_error:
                    self._post_json(web.base_url + "/api/v1/plain-unauthorized", {})
                with pytest.raises(urllib.error.HTTPError) as array_error:
                    self._post_json(web.base_url + "/api/v1/array-unauthorized", {})

        assert exc.value.code == HTTPStatus.BAD_GATEWAY.value
        assert payload == {
            "error": "backend authentication failed through openinfra-web",
            "reason": "server-side backend bearer token was not accepted by the API",
        }
        assert plain_error.value.code == HTTPStatus.UNAUTHORIZED.value
        assert array_error.value.code == HTTPStatus.UNAUTHORIZED.value
        assert "missing bearer token" not in json.dumps(payload)

    def test_entrypoint_returns_success_and_keyboard_interrupt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        parsed = __import__("openinfra.interfaces.web", fromlist=["OpenInfraWebEntrypoint"])
        config = self._config("http://127.0.0.1:8080")

        class ReturningServer:
            def __init__(self, _address: object, _config: object) -> None:
                self.started = False

            def serve_forever(self) -> None:
                self.started = True

        class InterruptingServer:
            def __init__(self, _address: object, _config: object) -> None:
                self.started = False

            def serve_forever(self) -> None:
                raise KeyboardInterrupt

        monkeypatch.setattr(
            parsed.OpenInfraWebConfigFactory, "from_args", lambda self, argv: config
        )
        monkeypatch.setattr(parsed, "OpenInfraWebServer", ReturningServer)
        assert parsed.OpenInfraWebEntrypoint.main() == 0
        monkeypatch.setattr(parsed, "OpenInfraWebServer", InterruptingServer)
        assert parsed.OpenInfraWebEntrypoint.main() == 0

    def _get_json(self, url: str) -> dict[str, object]:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _config(self, backend_url: str, backend_bearer_token: str = "") -> OpenInfraWebConfig:
        return OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url=backend_url,
            public_api_base_url="/api",
            public_api_docs_base_url="",
            static_root=OpenInfraWebStaticLocator().resolve(None),
            edition="pro",
            auth_mode="standard",
            allow_insecure_backend=True,
            backend_bearer_token=backend_bearer_token,
        )

    def _get_text(self, url: str) -> str:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8")

    def _post_json(
        self, url: str, payload: dict[str, object], browser_bearer: str = ""
    ) -> dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if browser_bearer:
            headers["Authorization"] = "Bearer " + browser_bearer
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


class TestOpenInfraWebEdges:
    def test_config_factory_and_validator_negative_branches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        config = OpenInfraWebConfigValidator()
        parsed = __import__("openinfra.interfaces.web", fromlist=["OpenInfraWebConfigFactory"])
        factory = parsed.OpenInfraWebConfigFactory()
        built = factory.from_args(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "2007",
                "--backend-url",
                "https://backend.example.net",
                "--public-api-base-url",
                "/api",
                "--static-root",
                str(static_root),
                "--edition",
                "enterprise",
                "--auth-mode",
                "ipa",
            ]
        )

        assert built.port == 2007
        assert built.static_root == static_root
        invalid_configs = [
            self._raw_config("ftp://backend.example.net", static_root),
            self._raw_config("https://backend.example.net/path", static_root),
            self._raw_config("https://backend.example.net", static_root, edition="unknown"),
            self._raw_config("https://backend.example.net", static_root, auth_mode="oauth"),
            self._raw_config(
                "https://backend.example.net", static_root, edition="lite", auth_mode="ldap"
            ),
            self._raw_config("https://backend.example.net", static_root, max_request_body_bytes=0),
            self._raw_config(
                "https://backend.example.net",
                static_root,
                database_dsn_ref="postgresql://cleartext/openinfra",
            ),
        ]
        for invalid in invalid_configs:
            with pytest.raises(OpenInfraError):
                config.validate(invalid)
        monkeypatch.setattr(parsed.sys, "argv", ["openinfra-web", "--backend-url", "ftp://bad"])
        assert parsed.OpenInfraWebEntrypoint.main() == 2

    def test_proxy_error_branches_head_and_non_api_routes(self) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            small_config = OpenInfraWebConfig(
                host="127.0.0.1",
                port=0,
                backend_url=backend.base_url,
                public_api_base_url="/api",
                public_api_docs_base_url="",
                static_root=static_root,
                edition="pro",
                auth_mode="standard",
                allow_insecure_backend=True,
                max_request_body_bytes=4,
                backend_bearer_token=_test_server_side_bearer(),
            )
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), small_config)) as web:
                head_request = urllib.request.Request(web.base_url + "/", method="HEAD")
                with urllib.request.urlopen(head_request, timeout=5) as head_response:
                    assert head_response.status == HTTPStatus.OK.value
                    assert head_response.read() == b""
                health = self._get_json(web.base_url + "/health")
                with pytest.raises(urllib.error.HTTPError) as missing:
                    self._get_json(web.base_url + "/api/v1/missing?tenant_id=default")
                with pytest.raises(urllib.error.HTTPError) as non_api:
                    delete = urllib.request.Request(web.base_url + "/not-api", method="DELETE")
                    urllib.request.urlopen(delete, timeout=5)
                with pytest.raises(urllib.error.HTTPError) as too_large:
                    request = urllib.request.Request(
                        web.base_url + "/api/v1/echo",
                        data=b"12345",
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(request, timeout=5)
                with pytest.raises(urllib.error.HTTPError) as put_non_api:
                    put = urllib.request.Request(
                        web.base_url + "/not-api", data=b"{}", method="PUT"
                    )
                    urllib.request.urlopen(put, timeout=5)
                with pytest.raises(urllib.error.HTTPError) as patch_non_api:
                    patch = urllib.request.Request(
                        web.base_url + "/not-api", data=b"{}", method="PATCH"
                    )
                    urllib.request.urlopen(patch, timeout=5)

        assert health["status"] == "ok"
        assert missing.value.code == HTTPStatus.NOT_FOUND.value
        assert non_api.value.code == HTTPStatus.NOT_FOUND.value
        assert put_non_api.value.code == HTTPStatus.NOT_FOUND.value
        assert patch_non_api.value.code == HTTPStatus.NOT_FOUND.value
        assert too_large.value.code == HTTPStatus.BAD_REQUEST.value

    def test_backend_unavailable_and_invalid_content_length(self) -> None:
        import http.client

        static_root = OpenInfraWebStaticLocator().resolve(None)
        unavailable = OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url="http://127.0.0.1:9",
            public_api_base_url="/api",
            public_api_docs_base_url="",
            static_root=static_root,
            edition="pro",
            auth_mode="standard",
            allow_insecure_backend=True,
        )
        with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), unavailable)) as web:
            with pytest.raises(urllib.error.HTTPError) as ready:
                self._get_json(web.base_url + "/ready")
            with pytest.raises(urllib.error.HTTPError) as api:
                self._get_json(web.base_url + "/api/v1/version")

        assert ready.value.code == HTTPStatus.SERVICE_UNAVAILABLE.value
        assert api.value.code == HTTPStatus.BAD_GATEWAY.value
        with (
            RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend,
            RunningServer(
                OpenInfraWebServer(("127.0.0.1", 0), self._config(backend.base_url))
            ) as web,
        ):
            connection = http.client.HTTPConnection("127.0.0.1", web.server.server_port, timeout=5)
            connection.putrequest("POST", "/api/v1/echo")
            connection.putheader("Content-Length", "invalid")
            connection.endheaders()
            response = connection.getresponse()
            payload = response.read().decode("utf-8")
            connection.close()

        assert response.status == HTTPStatus.BAD_REQUEST.value
        assert "invalid Content-Length" in payload

    def test_entrypoint_returns_success_and_keyboard_interrupt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        parsed = __import__("openinfra.interfaces.web", fromlist=["OpenInfraWebEntrypoint"])
        config = self._config("http://127.0.0.1:8080")

        class ReturningServer:
            def __init__(self, _address: object, _config: object) -> None:
                self.started = False

            def serve_forever(self) -> None:
                self.started = True

        class InterruptingServer:
            def __init__(self, _address: object, _config: object) -> None:
                self.started = False

            def serve_forever(self) -> None:
                raise KeyboardInterrupt

        monkeypatch.setattr(
            parsed.OpenInfraWebConfigFactory, "from_args", lambda self, argv: config
        )
        monkeypatch.setattr(parsed, "OpenInfraWebServer", ReturningServer)
        assert parsed.OpenInfraWebEntrypoint.main() == 0
        monkeypatch.setattr(parsed, "OpenInfraWebServer", InterruptingServer)
        assert parsed.OpenInfraWebEntrypoint.main() == 0

    def _get_json(self, url: str) -> dict[str, object]:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _config(self, backend_url: str) -> OpenInfraWebConfig:
        return OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url=backend_url,
            public_api_base_url="/api",
            public_api_docs_base_url="",
            static_root=OpenInfraWebStaticLocator().resolve(None),
            edition="pro",
            auth_mode="standard",
            allow_insecure_backend=True,
        )

    def _raw_config(
        self,
        backend_url: str,
        static_root: Path,
        edition: str = "pro",
        auth_mode: str = "standard",
        max_request_body_bytes: int = 1_048_576,
        database_dsn_ref: str = "",
    ) -> OpenInfraWebConfig:
        return OpenInfraWebConfig(
            host="127.0.0.1",
            port=2006,
            backend_url=backend_url,
            public_api_base_url="/api",
            public_api_docs_base_url="",
            static_root=static_root,
            edition=edition,
            auth_mode=auth_mode,
            allow_insecure_backend=False,
            max_request_body_bytes=max_request_body_bytes,
            database_dsn_ref=database_dsn_ref,
        )
