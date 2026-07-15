# Kubernetes GitOps drift operations

## Purpose

This runbook governs the import of GitOps expected state and the comparison with Kubernetes state observed by OpenInfra Discovery.

## Preconditions

1. A Kubernetes topology snapshot exists for the target tenant and cluster.
2. The operator has the Kubernetes read/write permissions required by the selected operation.
3. The Git revision is a full immutable 40- or 64-character hexadecimal commit digest.
4. The expected resource file contains no secret value, credential, private key, token or sensitive metadata key.

## Import expected state

Use either the HTTP endpoint or CLI command:

```text
openinfra kubernetes gitops-import \
  --tenant <tenant> \
  --admin-token <token> \
  --cluster-key <cluster> \
  --repository-ref <repository> \
  --revision <full-commit-digest> \
  --source-path <relative-path> \
  --owner <owner> \
  --environment <environment> \
  --captured-at <ISO-8601> \
  --resources-file <expected-resources.json> \
  --policy-file <gitops-policy.json>
```

Imports are idempotent by fingerprint. Re-importing the same immutable expected state returns the existing state instead of creating a duplicate.

## Assess drift

For explicit state identifiers:

```text
openinfra kubernetes gitops-drift \
  --tenant <tenant> \
  --admin-token <token> \
  --expected-state-id <state-id> \
  --observed-snapshot-id <snapshot-id>
```

For the latest expected and observed state of one cluster:

```text
openinfra kubernetes gitops-latest-drift \
  --tenant <tenant> \
  --admin-token <token> \
  --cluster-key <cluster>
```

## Interpretation

`status=compliant` means no governed difference was found. `status=drift` means one or more explicit differences exist. Drift kinds include missing/unexpected resources, missing or mismatched labels/annotations, owner or environment violations, and expected attribute mismatches.

Every report includes immutable fingerprints for the expected state, observed snapshot and assessment itself.

## Safety rule

OpenInfra never applies a corrective action from this capability. `automatic_remediation=false` is contractual. Remediation remains an explicit external GitOps workflow under human and repository governance.
