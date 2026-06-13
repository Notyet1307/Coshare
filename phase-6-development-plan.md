# Phase 6 Development Plan

Version: 0.1
Phase: Execution Platform Delegation POC
Canonical task source: repo milestone doc
Execution backend: external platform evidence only, offline fixture first
Default network behavior: offline / no network
Default remote write behavior: none

---

## Decision

Phase 6 proves the architecture boundary between Coshare and an external execution substrate such as Multica, OpenHands, OpenCode, Goose, or a similar agent runtime.

Coshare does not become the execution platform.

External platform state is execution evidence only.

Bridge gate remains the final acceptance authority.

```text
External completed != accepted.
Agent says done != accepted.
GitHub Issue closed != accepted.
PR merged != accepted.
CI passed != accepted.
Bridge gate accepted == accepted.
```

## Scope

Allowed:

- define execution platform delegation rules
- define backend-neutral external execution evidence
- add minimal Bridge gate support for local `external-execution.yaml`
- use offline Multica-like fixtures or local evidence only
- prove external completed does not bypass verifier, reviewer, path-policy, blocker, PR/CI, issue, delivery, or closeout gates
- produce a Phase 7 decision recommendation

Forbidden:

- live Multica integration
- Multica API calls
- GitLab integration
- dashboard
- scheduler
- worker registry
- autonomous loop
- automatic PR creation
- push automation
- auto-merge
- live GitHub writes
- model API calls inside Bridge
- token or secret storage
- VPN or internal network automation

## Bridge Boundary

Bridge may read local external execution evidence when a task declares:

```yaml
required_external_execution_evidence:
  - execution
```

Bridge must not create or update external execution items in Phase 6.

Bridge must not call model APIs or external platform APIs.

## Gate Rules

- missing required external execution evidence -> `inconclusive`
- external execution failed -> `failed`
- external execution blocked -> `inconclusive`
- external execution completed with missing verifier, reviewer, or path-policy evidence -> `inconclusive`
- external execution completed with any Bridge gate failure -> `failed`
- external execution completed does not produce `accepted` by itself
- `accepted` requires normal Bridge evidence gates to pass

## Acceptance

Phase 6 is acceptable when:

- M1 through M6 milestone docs validate.
- external execution evidence schema is documented.
- Bridge gate consumes local `external-execution.yaml` when required.
- tests cover missing external evidence, failed external evidence, and completed external evidence without normal Bridge evidence.
- no network, live GitHub writes, Multica API calls, model API calls, token storage, scheduler, dashboard, worker registry, push automation, PR creation, or merge automation is added.

## Phase 7 Decision

Phase 6 should end with a recommendation:

- continue to a live Multica POC,
- test OpenHands or another execution substrate,
- stay GitHub-only,
- or keep Coshare self-contained.
