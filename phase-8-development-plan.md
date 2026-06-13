# Phase 8 Development Plan

Version: 0.1
Phase: Real Multica Manual Trial
Canonical task source: repo milestone doc
Execution backend: real Multica task state copied manually into local evidence
Default network behavior: no Bridge network access
Default remote write behavior: none

---

## Decision

Phase 8 prepares a real manual Multica task trial.

The purpose is to verify whether a real Multica task can serve as the external execution substrate for Coshare while Bridge remains the final acceptance authority.

Phase 8 is not a Multica adapter.

## Scope

Allowed:

- define the real manual Multica trial
- document exact manual Multica steps
- create a template-only `external-execution.yaml`
- keep Bridge consuming local evidence only
- prepare decision options for the next phase

Forbidden:

- Multica API integration
- calling Multica APIs
- making Bridge a Multica client
- live reads inside Bridge gate
- writing Multica comments from Bridge
- storing Multica tokens or secrets
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

## Acceptance

Phase 8 is acceptable only as a prepared manual trial when:

- `docs/milestones/M8.md` validates.
- `docs/agent/multica-manual-trial.md` contains the manual checklist.
- `docs/milestones/evidence/M8-T01/external-execution.yaml` is clearly marked as a template, not real evidence.
- M8-T01 requires external execution, path-policy, verifier, and reviewer evidence.
- No passing path-policy, verifier, or reviewer evidence is created solely to mark M8 accepted.
- No Bridge code is modified unless a clear failing test requires it.

## Decision Options

Do not choose an outcome before the manual trial.

Possible outcomes:

- Continue to Multica read-only export adapter.
- Continue manual-export only.
- Try OpenHands instead.
- Stay GitHub-only.
- Pause external platform work.
