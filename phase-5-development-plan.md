# Phase 5 Development Plan

Version: 0.1
Phase: GitHub Delivery Linkage and Acceptance Publication
Canonical task source: repo milestone doc
Default network behavior: offline / no network unless explicitly requested
Default remote write behavior: dry-run only

---

## Decision

Phase 5 connects the existing repo-doc task model, GitHub Issue execution tickets, GitHub PR/CI evidence, review evidence, Bridge gate, and closeout into one auditable delivery chain.

Milestone docs remain canonical.

GitHub Issues remain execution tickets and collaboration surfaces only.

GitHub PRs, CI checks, reviews, issue comments, PR comments, and labels are evidence or publication surfaces only.

Bridge gate remains the final acceptance authority.

---

## Scope

Allowed:

- define delivery linkage governance
- define acceptance publication rules
- define GitHub comment boundaries
- generate delivery plans from milestone task contracts and existing evidence
- generate structured delivery linkage evidence
- generate dry-run managed status comments
- write local structured evidence under `docs/milestones/evidence/<task_id>/`
- integrate delivery linkage into Bridge gate and closeout
- use offline fixtures for tests and dogfood

Forbidden:

- GitHub Issue as canonical task source
- automatic milestone-doc updates from GitHub Issue body
- GitHub Projects integration
- GitLab integration
- Multica integration
- dashboard
- auto-merge
- automatic PR creation
- push automation
- model API calls inside Bridge
- autonomous long-running loops
- worker metrics routing
- bidirectional sync
- production secret handling
- storing GitHub tokens in repo files
- VPN/internal network automation

---

## Bridge Commands

Phase 5 adds:

- `delivery-plan`
- `delivery-link`
- `delivery-status`
- `publish-status`
- `delivery-closeout`

All live GitHub operations must be explicit.

This phase uses dry-run and offline fixture mode for local verification.

---

## Evidence

Expected files:

- `delivery-linkage.yaml`
- `acceptance-publication.yaml`
- `github-status-comment.yaml`

Delivery evidence must summarize facts and links. It must not store raw CI logs, raw issue comments, raw PR comments, tokens, auth headers, or credential output.

---

## Gate Rules

Bridge gate may consume delivery evidence when a task contract declares `required_delivery_evidence`.

Rules:

- missing required delivery evidence is `inconclusive`
- issue marker mismatch is `failed`
- PR head SHA mismatch against CI/verifier/reviewer evidence is `failed`
- CI failure is `failed`
- missing required CI evidence is `inconclusive`
- PR merged but Bridge gate not accepted is `inconclusive`
- Issue closed but Bridge gate not accepted is `inconclusive`
- duplicate managed status comments are `inconclusive`
- live GitHub unavailable is `inconclusive`

Issue closed state, PR merged state, and CI passed state are never final acceptance by themselves.

---

## Closeout

Closeout must include delivery linkage facts:

- issue URL
- PR URL
- PR head SHA
- CI/check status
- review status
- gate result
- publication status
- whether remote write occurred

Do not mark failed or inconclusive delivery linkage as accepted.

---

## Acceptance

Phase 5 is acceptable when:

- M1, M2, M3, M4, and M5 validate
- existing tests still pass
- delivery commands work in offline/dry-run mode
- required failure scenarios are tested
- M5 evidence and closeout exist
- no live GitHub write occurred
- no token was stored or printed

If implementation changes are not committed, do not claim final accepted from stable SHA evidence.
