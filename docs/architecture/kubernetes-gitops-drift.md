# Kubernetes GitOps drift architecture

## Scope

EPIC-2104 adds a governed comparison between immutable GitOps expected states and immutable Kubernetes observations already captured by Discovery. The capability is deliberately evaluative: it does not apply manifests, patch clusters, reconcile controllers, or silently remediate drift.

## Sources of truth

- **Expected state**: `KubernetesGitOpsState`, imported from a Git repository reference, a full 40/64 hexadecimal commit digest, a relative source path, owner, environment, policy and bounded expected resources.
- **Observed state**: `KubernetesTopologySnapshot`, produced by the existing Kubernetes Discovery inventory.
- **Assessment**: `KubernetesGitOpsComplianceReport`, computed deterministically from one expected state and one observed snapshot.

The two sources remain independent and immutable. The assessment stores no duplicate cluster state.

## Governance model

A `KubernetesGitOpsPolicy` controls only explicitly governed dimensions:

- required labels;
- required annotations;
- owner metadata;
- environment metadata;
- allowed environments;
- optional detection of unexpected observed resources.

Volatile Kubernetes fields are not compared unless they are explicitly present in the expected resource attributes. This prevents false drift caused by runtime-generated metadata.

## Security properties

- repository references reject embedded passwords and unsupported URL schemes;
- Git revisions must be full immutable commit digests;
- source paths are relative and reject traversal segments;
- sensitive metadata keys are rejected;
- payloads are bounded to the Kubernetes inventory scale limit;
- drift assessment is read-only against both expected and observed state;
- `automatic_remediation` is always `false`.

## Persistence

Migration `0056_kubernetes_gitops_drift.sql` adds tenant-partitioned expected-state storage and a transactional outbox. The expected state payload is immutable and fingerprinted. Reads support cursor pagination and indexed filtering by cluster, environment and owner.

## Interfaces

The same capability is exposed through HTTP, CLI and the Discovery web catalogue:

- import expected state;
- list states;
- get a state;
- get latest state for a cluster;
- assess one expected state against one observed snapshot;
- assess the latest expected and observed states for a cluster.

## Audit and events

Imports are audited as `kubernetes.gitops.state.imported`. Assessments are audited as `kubernetes.gitops.assessed`. A drift result additionally emits `kubernetes.gitops.drift.detected` through the transactional outbox.
