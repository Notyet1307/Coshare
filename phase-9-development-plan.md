# Phase 9 Development Plan

Version: 0.1
Phase: Bridge Simplification and Manual Operating Surface
Canonical task source: repo milestone doc
Default network behavior: no new network behavior
Default remote write behavior: none

---

## Decision

Phase 9 does not add automation.

It makes the existing Phase 1 through Phase 8 architecture easier to understand and use by defining a smaller daily operating model.

Existing advanced Bridge capabilities stay available. They are classified as optional evidence adapters instead of being part of the default mental model.

The simplified model is:

```text
Coshare Bridge only answers:
"Can this task be accepted?"
```

Bridge is not an execution platform, scheduler, dashboard, worker registry, Multica client, GitHub client, or model runner.

---

## Default Daily Concepts

Daily users should understand only these concepts first:

1. task contract
2. external execution evidence
3. path-policy evidence
4. verifier evidence
5. reviewer evidence
6. gate report
7. closeout

---

## Default Daily Commands

Daily users should start with only five commands:

- `validate`
- `task-info`
- `diff-check`
- `gate`
- `closeout`

---

## Optional / Advanced Commands

These commands remain supported, but they are optional:

- `evidence-init`
- `prompt-pack`
- `github-evidence`
- `issue-plan`
- `issue-export`
- `issue-status`
- `issue-comment`
- `delivery-plan`
- `delivery-link`
- `delivery-status`
- `publish-status`
- `delivery-closeout`

Use them only for formal PR / CI / Issue / delivery workflows.

---

## Scope

Allowed:

- define Bridge Lite
- define the default evidence packet
- define the daily operating flow
- classify advanced evidence adapters
- create M9 milestone docs
- create interim M9 closeout

Forbidden:

- new platform integrations
- Multica API integration
- Multica API calls
- scheduler
- dashboard
- worker registry
- autonomous loop
- bidirectional sync
- automatic PR creation
- push automation
- auto-merge
- model API calls
- GitLab integration
- GitHub Projects integration
- new CLI commands
- new evidence types
- adapter code
- passing evidence solely to mark M9 accepted

---

## Acceptance

Phase 9 is acceptable as a simplification package when:

- `docs/milestones/M9.md` validates.
- Daily workflow is understandable without reading Phase 1 through Phase 8 plans.
- Bridge code is not expanded.
- Advanced commands are documented as optional.
- No live integration is added.
- No existing tests are broken.

M9 interim closeout must not claim Bridge gate acceptance unless evidence later proves it.
