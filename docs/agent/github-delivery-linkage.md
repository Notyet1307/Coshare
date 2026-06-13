# GitHub Delivery Linkage

Phase 5 defines the delivery chain:

```text
task -> issue -> PR -> CI/review -> Bridge gate -> closeout
```

Milestone docs remain canonical.

GitHub surfaces are evidence and publication surfaces only.

---

## Evidence File

File:

```text
delivery-linkage.yaml
```

Minimum shape:

```yaml
schema_version: 1
task_id: M5-T01
repository: Notyet1307/Coshare
issue_number: 501
issue_url: https://github.com/Notyet1307/Coshare/issues/501
pr_number: 5
pr_url: https://github.com/Notyet1307/Coshare/pull/5
pr_head_sha: abc123
verifier_head_sha: abc123
reviewer_head_sha: abc123
ci_head_sha: abc123
path_policy_result: pass
ci_result: pass
review_result: pass
bridge_gate_result: accepted
closeout_ref: docs/milestones/closeout/M5.md
drift_detected: false
drift_reasons: []
linkage_status: accepted
generated_at: "2026-06-13T00:00:00Z"
conclusion: pass
```

---

## Drift

Failed drift:

- issue marker task ID does not match milestone task ID
- issue canonical owner marker is not `repo-doc`
- PR head SHA conflicts with CI/verifier/reviewer evidence
- CI/check evidence failed
- review evidence failed

Inconclusive drift:

- issue revision marker is stale
- CI/check evidence is required but missing
- PR is merged but Bridge gate is not accepted
- Issue is closed but Bridge gate is not accepted
- closeout block is missing when required

Bridge must detect drift. It must not silently repair milestone scope from GitHub.

---

## Status Values

Delivery status may be:

- `linked`
- `unlinked`
- `stale`
- `conflict`
- `ready_to_publish`
- `accepted`
- `failed`
- `inconclusive`

Only Bridge gate accepted can support final acceptance.
