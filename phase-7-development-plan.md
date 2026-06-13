# Phase 7 Development Plan

Version: 0.1
Phase: Multica Live Execution Evidence POC
Canonical task source: repo milestone doc
Execution backend: Multica state represented by local manual-export evidence
Default network behavior: no Bridge network access
Default remote write behavior: none

---

## Decision

Phase 7 proves that a real Multica task can be represented as local Coshare evidence while Bridge gate remains the final acceptance authority.

Coshare does not become a Multica client or execution platform in this phase.

```text
Multica completed != accepted.
Bridge gate accepted == accepted.
```

## Scope

Allowed:

- define the manual-export Multica evidence POC
- document how a human copies Multica task state into local evidence
- keep evidence backend-neutral through `external-execution.yaml`
- add offline/manual-export fixture examples
- test that Multica completed does not imply Bridge accepted

Forbidden:

- calling Multica APIs from Bridge
- creating or updating Multica tasks from Bridge
- reading Multica live state inside Bridge gate
- writing Multica comments from Bridge
- treating Multica issue/task state as canonical
- treating Multica completed as accepted
- storing Multica tokens
- adding long-running daemon behavior to Coshare
- scheduler, worker registry, dashboard, autonomous loop, bidirectional sync
- automatic PR creation, push automation, auto-merge
- model API calls
- GitLab integration
- GitHub Projects integration

## Ownership

Multica owns execution state.

Coshare owns:

- stable `task_id`
- task contract
- evidence
- path-policy
- verifier and reviewer checks
- Bridge gate
- closeout

GitHub owns repo, PR, CI, and review facts.

Bridge consumes local evidence only.

## Acceptance

Phase 7 is acceptable when:

- `docs/milestones/M7.md` validates.
- `docs/milestones/evidence/M7-T01/external-execution.yaml` records a Multica manual-export or offline fixture state.
- Bridge gate for M7-T01 is `inconclusive` when normal path-policy, verifier, and reviewer evidence are missing.
- tests prove Multica completed does not bypass Bridge gate.
- no live Multica API call, token storage, live GitHub write, scheduler, dashboard, worker registry, push, PR creation, merge automation, or model API behavior is added.

## Phase 8 Decision

After this POC, decide whether to:

- continue Multica with a constrained read-only export workflow,
- test OpenHands as the execution substrate,
- stay GitHub-only,
- or pause external platform work.
