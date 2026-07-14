from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from openinfra.domain.certificate_pki import CertificateAsset
from openinfra.domain.common import EntityId, ValidationError
from openinfra.domain.sbom import FindingStatus, RiskFinding, SbomDocument


@dataclass(frozen=True, slots=True)
class KubernetesImageReference:
    reference: str
    digest: str | None
    sbom_document_ids: tuple[str, ...]

    _REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,1023}")
    _DIGEST = re.compile(r"sha256:[a-f0-9]{64}")

    @classmethod
    def create(
        cls,
        reference: str,
        digest: str | None = None,
        sbom_document_ids: tuple[str, ...] = (),
    ) -> Self:
        normalized_reference = reference.strip()
        if (
            "://" in normalized_reference
            or not cls._REFERENCE.fullmatch(normalized_reference)
            or any(character.isspace() for character in normalized_reference)
        ):
            raise ValidationError("Kubernetes image reference is invalid")
        embedded_digest: str | None = None
        if "@sha256:" in normalized_reference.lower():
            prefix, _, raw_digest = normalized_reference.rpartition("@")
            candidate = raw_digest.lower()
            if not prefix or not cls._DIGEST.fullmatch(candidate):
                raise ValidationError("Kubernetes image digest is invalid")
            normalized_reference = f"{prefix}@{candidate}"
            embedded_digest = candidate
        normalized_digest = cls._normalize_digest(digest)
        if embedded_digest is not None and normalized_digest not in {None, embedded_digest}:
            raise ValidationError("Kubernetes image digest conflicts with the image reference")
        documents = tuple(
            sorted({EntityId.from_value(item).value for item in sbom_document_ids if item.strip()})
        )
        if len(documents) > 32:
            raise ValidationError(
                "Kubernetes image reference cannot link more than 32 SBOM documents"
            )
        return cls(normalized_reference, normalized_digest or embedded_digest, documents)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        raw_ids = payload.get("sbom_document_ids") or []
        if not isinstance(raw_ids, list):
            raise ValidationError("sbom_document_ids must be a JSON array")
        return cls.create(
            reference=str(payload.get("reference") or ""),
            digest=None if payload.get("digest") is None else str(payload["digest"]),
            sbom_document_ids=tuple(str(item) for item in raw_ids),
        )

    @classmethod
    def _normalize_digest(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().lower()
        if re.fullmatch(r"[a-f0-9]{64}", normalized):
            normalized = f"sha256:{normalized}"
        if not cls._DIGEST.fullmatch(normalized):
            raise ValidationError("Kubernetes image digest must be a SHA-256 digest")
        return normalized

    @property
    def correlation_key(self) -> str:
        return self.digest or self.reference

    def as_dict(self) -> dict[str, object]:
        return {
            "reference": self.reference,
            "digest": self.digest,
            "sbom_document_ids": list(self.sbom_document_ids),
        }


@dataclass(frozen=True, slots=True)
class KubernetesSecretReference:
    provider: str
    display_reference: str
    reference_hash: str

    _ALLOWED_PREFIXES = (
        "vault://",
        "sops://",
        "kms://",
        "kubernetes-secret://",
        "external-secret://",
        "aws-secrets-manager://",
        "azure-key-vault://",
        "gcp-secret-manager://",
    )
    _SAFE_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,2047}")

    @classmethod
    def create(cls, value: str) -> Self:
        normalized = value.strip()
        prefix = next((item for item in cls._ALLOWED_PREFIXES if normalized.startswith(item)), None)
        if prefix is None or not cls._SAFE_REFERENCE.fullmatch(normalized):
            raise ValidationError(
                "Kubernetes secret reference must use an approved external reference scheme"
            )
        suffix = normalized[len(prefix) :]
        if not suffix or suffix.startswith("/") or suffix.endswith("/"):
            raise ValidationError("Kubernetes secret reference path is invalid")
        provider = prefix[:-3]
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if prefix == "kubernetes-secret://":
            parts = suffix.split("/")
            if len(parts) != 2 or any(not part.strip() for part in parts):
                raise ValidationError(
                    "kubernetes-secret references must use kubernetes-secret://namespace/name"
                )
            display = normalized
        else:
            display = f"{prefix}***"
        return cls(provider, display, digest)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        provider = str(payload.get("provider") or "").strip().lower()
        display = str(payload.get("display_reference") or "").strip()
        digest = str(payload.get("reference_hash") or "").strip().lower()
        if provider not in {prefix[:-3] for prefix in cls._ALLOWED_PREFIXES}:
            raise ValidationError("Kubernetes secret reference provider is unsupported")
        if provider == "kubernetes-secret":
            recreated = cls.create(display)
            if recreated.reference_hash != digest:
                raise ValidationError("Kubernetes secret reference hash mismatch")
            return recreated
        if display != f"{provider}://***" or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValidationError("Kubernetes secret reference persisted representation is invalid")
        return cls(provider, display, digest)

    def as_dict(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "display_reference": self.display_reference,
            "reference_hash": self.reference_hash,
        }


@dataclass(frozen=True, slots=True)
class KubernetesImageSecurityContext:
    reference: str
    digest: str | None
    sbom_documents: tuple[dict[str, object], ...]
    findings: tuple[dict[str, object], ...]
    sbom_missing: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "reference": self.reference,
            "digest": self.digest,
            "sbom_documents": list(self.sbom_documents),
            "findings": list(self.findings),
            "sbom_missing": self.sbom_missing,
        }


@dataclass(frozen=True, slots=True)
class KubernetesCertificateSecurityContext:
    fingerprint: str
    found: bool
    lifecycle: str | None
    health: str | None
    days_remaining: int | None
    owner: str | None
    environment: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "found": self.found,
            "lifecycle": self.lifecycle,
            "health": self.health,
            "days_remaining": self.days_remaining,
            "owner": self.owner,
            "environment": self.environment,
        }


@dataclass(frozen=True, slots=True)
class KubernetesResourceSecurityContext:
    resource_uid: str
    kind: str
    name: str
    namespace: str | None
    images: tuple[KubernetesImageSecurityContext, ...]
    certificates: tuple[KubernetesCertificateSecurityContext, ...]
    secret_references: tuple[dict[str, str], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "resource_uid": self.resource_uid,
            "kind": self.kind,
            "name": self.name,
            "namespace": self.namespace,
            "images": [item.as_dict() for item in self.images],
            "certificates": [item.as_dict() for item in self.certificates],
            "secret_references": list(self.secret_references),
        }


@dataclass(frozen=True, slots=True)
class KubernetesSecurityCorrelationReport:
    snapshot_id: str
    cluster_key: str
    observed_at: datetime
    fingerprint: str
    resources: tuple[KubernetesResourceSecurityContext, ...]
    image_count: int
    images_without_sbom: int
    active_vulnerability_count: int
    critical_vulnerability_count: int
    certificate_count: int
    unknown_certificate_count: int
    unhealthy_certificate_count: int
    secret_reference_count: int
    correlation_truncated: bool

    @classmethod
    def build(
        cls,
        *,
        snapshot: Any,
        sbom_documents: tuple[SbomDocument, ...],
        findings: tuple[RiskFinding, ...],
        certificates: dict[str, CertificateAsset],
        correlation_truncated: bool,
    ) -> Self:
        documents_by_id = {item.id.value: item for item in sbom_documents}
        findings_by_document: dict[str, list[RiskFinding]] = {}
        for finding in findings:
            findings_by_document.setdefault(finding.document_id, []).append(finding)

        resources: list[KubernetesResourceSecurityContext] = []
        image_count = 0
        images_without_sbom = 0
        active_vulnerability_count = 0
        critical_vulnerability_count = 0
        certificate_count = 0
        unknown_certificate_count = 0
        unhealthy_certificate_count = 0
        secret_reference_count = 0

        for resource in snapshot.resources:
            image_contexts: list[KubernetesImageSecurityContext] = []
            for image in resource.images:
                matched = cls._matching_documents(image, sbom_documents, documents_by_id)
                matched_findings = tuple(
                    sorted(
                        (
                            finding
                            for document in matched
                            for finding in findings_by_document.get(document.id.value, [])
                        ),
                        key=lambda item: (
                            item.priority.value,
                            item.cve_id,
                            item.component_name,
                            item.id.value,
                        ),
                    )
                )
                active = tuple(
                    item
                    for item in matched_findings
                    if item.status not in {FindingStatus.MITIGATED, FindingStatus.FALSE_POSITIVE}
                )
                image_count += 1
                if not matched:
                    images_without_sbom += 1
                active_vulnerability_count += len(active)
                critical_vulnerability_count += sum(
                    1 for item in active if item.priority.value == "critical"
                )
                image_contexts.append(
                    KubernetesImageSecurityContext(
                        reference=image.reference,
                        digest=image.digest,
                        sbom_documents=tuple(cls._document_summary(item) for item in matched),
                        findings=tuple(cls._finding_summary(item) for item in matched_findings),
                        sbom_missing=not matched,
                    )
                )

            certificate_contexts: list[KubernetesCertificateSecurityContext] = []
            for fingerprint in resource.certificate_fingerprints:
                certificate_count += 1
                certificate = certificates.get(fingerprint)
                if certificate is None:
                    unknown_certificate_count += 1
                    certificate_contexts.append(
                        KubernetesCertificateSecurityContext(
                            fingerprint, False, None, None, None, None, None
                        )
                    )
                    continue
                health = certificate.health(snapshot.observed_at)
                if health.value != "healthy":
                    unhealthy_certificate_count += 1
                certificate_contexts.append(
                    KubernetesCertificateSecurityContext(
                        fingerprint=fingerprint,
                        found=True,
                        lifecycle=certificate.lifecycle.value,
                        health=health.value,
                        days_remaining=certificate.days_remaining(snapshot.observed_at),
                        owner=certificate.owner,
                        environment=certificate.environment,
                    )
                )

            secret_reference_count += len(resource.secret_refs)
            if image_contexts or certificate_contexts or resource.secret_refs:
                resources.append(
                    KubernetesResourceSecurityContext(
                        resource_uid=resource.uid,
                        kind=resource.kind.value,
                        name=resource.name,
                        namespace=resource.namespace,
                        images=tuple(image_contexts),
                        certificates=tuple(certificate_contexts),
                        secret_references=tuple(item.as_dict() for item in resource.secret_refs),
                    )
                )

        normalized_resources = tuple(
            sorted(
                resources,
                key=lambda item: (item.namespace or "", item.kind, item.name, item.resource_uid),
            )
        )
        payload = {
            "snapshot_id": snapshot.id.value,
            "cluster_key": snapshot.cluster_key,
            "observed_at": snapshot.observed_at.isoformat(),
            "resources": [item.as_dict() for item in normalized_resources],
            "image_count": image_count,
            "images_without_sbom": images_without_sbom,
            "active_vulnerability_count": active_vulnerability_count,
            "critical_vulnerability_count": critical_vulnerability_count,
            "certificate_count": certificate_count,
            "unknown_certificate_count": unknown_certificate_count,
            "unhealthy_certificate_count": unhealthy_certificate_count,
            "secret_reference_count": secret_reference_count,
            "correlation_truncated": correlation_truncated,
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()
        return cls(
            snapshot_id=snapshot.id.value,
            cluster_key=snapshot.cluster_key,
            observed_at=snapshot.observed_at,
            fingerprint=fingerprint,
            resources=normalized_resources,
            image_count=image_count,
            images_without_sbom=images_without_sbom,
            active_vulnerability_count=active_vulnerability_count,
            critical_vulnerability_count=critical_vulnerability_count,
            certificate_count=certificate_count,
            unknown_certificate_count=unknown_certificate_count,
            unhealthy_certificate_count=unhealthy_certificate_count,
            secret_reference_count=secret_reference_count,
            correlation_truncated=correlation_truncated,
        )

    @staticmethod
    def _matching_documents(
        image: KubernetesImageReference,
        documents: tuple[SbomDocument, ...],
        documents_by_id: dict[str, SbomDocument],
    ) -> tuple[SbomDocument, ...]:
        matched: dict[str, SbomDocument] = {
            document_id: documents_by_id[document_id]
            for document_id in image.sbom_document_ids
            if document_id in documents_by_id
        }
        for document in documents:
            if KubernetesSecurityCorrelationReport._document_matches_image(document, image):
                matched[document.id.value] = document
        return tuple(
            sorted(
                matched.values(),
                key=lambda item: (
                    item.application,
                    item.environment,
                    item.document_version,
                    item.id.value,
                ),
            )
        )

    @staticmethod
    def _document_matches_image(document: SbomDocument, image: KubernetesImageReference) -> bool:
        metadata = document.metadata
        references = KubernetesSecurityCorrelationReport._metadata_strings(
            metadata, "image_reference", "image_references", "container_image", "container_images"
        )
        digests = KubernetesSecurityCorrelationReport._metadata_strings(
            metadata, "image_digest", "image_digests", "container_image_digest"
        )
        if image.reference in references:
            return True
        return image.digest is not None and image.digest in {item.lower() for item in digests}

    @staticmethod
    def _metadata_strings(metadata: dict[str, Any], *keys: str) -> set[str]:
        result: set[str] = set()
        for key in keys:
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                result.add(value.strip())
            elif isinstance(value, list):
                result.update(str(item).strip() for item in value if str(item).strip())
        return result

    @staticmethod
    def _document_summary(document: SbomDocument) -> dict[str, object]:
        return {
            "id": document.id.value,
            "application": document.application,
            "release": document.release,
            "environment": document.environment,
            "format": document.format.value,
            "document_version": document.document_version,
            "component_count": document.component_count,
            "source_hash": document.source_hash,
        }

    @staticmethod
    def _finding_summary(finding: RiskFinding) -> dict[str, object]:
        return {
            "id": finding.id.value,
            "document_id": finding.document_id,
            "component_ref": finding.component_ref,
            "component_name": finding.component_name,
            "component_version": finding.component_version,
            "component_purl": finding.component_purl,
            "cve_id": finding.cve_id,
            "contextual_score": str(finding.contextual_score),
            "priority": finding.priority.value,
            "status": finding.status.value,
            "reasons": list(finding.reasons),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "cluster_key": self.cluster_key,
            "observed_at": self.observed_at.isoformat(),
            "fingerprint": self.fingerprint,
            "summary": {
                "resource_count": len(self.resources),
                "image_count": self.image_count,
                "images_without_sbom": self.images_without_sbom,
                "active_vulnerability_count": self.active_vulnerability_count,
                "critical_vulnerability_count": self.critical_vulnerability_count,
                "certificate_count": self.certificate_count,
                "unknown_certificate_count": self.unknown_certificate_count,
                "unhealthy_certificate_count": self.unhealthy_certificate_count,
                "secret_reference_count": self.secret_reference_count,
                "correlation_truncated": self.correlation_truncated,
            },
            "resources": [item.as_dict() for item in self.resources],
        }
