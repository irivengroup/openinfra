## v0.29.75 — Traçabilité ITAM partenaires fournisseurs/supports

| Élément | Traçabilité |
| --- | --- |
| Exigence | `REQ-00816` |
| Test CDC | `TST-WEB-115` |
| Test roadmap | `TST-P14-ITAM-PARTNER-REGISTRY` |
| Domaine | `openinfra.domain.itam.ItamPartner` |
| Application | `openinfra.application.itam_services.ItamSupportService` |
| CLI | `openinfra itam partner-*` |
| API | `/api/v1/itam/partner*` |
| UI | contexte ITAM `Fournisseurs et Supports` |
| Migration | `0032_itam_partner_registry.sql` |

## v0.29.73 — Traçabilité DCIM dépendances CRUD

| Élément | Traçabilité |
| --- | --- |
| Exigence | `REQ-00813` |
| Test CDC | `TST-WEB-112` |
| Test roadmap | `TST-P10-DCIM-DEPENDENCY-CRUD` |
| Domaine | `openinfra.domain.dcim` |
| Application | `openinfra.application.dcim_services.DcimTopologyService` |
| CLI | `openinfra dcim building-*`, `floor-*`, `room-*`, `zone-*` |
| API | `/api/v1/dcim/building/*`, `/floor/*`, `/room/*`, `/zone/*` |
| UI | contexte DCIM `Sites & dépendances` |
