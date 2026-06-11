# Milestone Template

## Scope

Describe the milestone scope.

## Non-Goals

List explicit non-goals.

## Task List

### MX-T01: Task title

```yaml task-contract
schema_version: 1
task_id: MX-T01
title: Task title
canonical_owner: repo-doc
revision: 1
mode: direct
risk: low
lifecycle_status: proposed

allowed_paths:
  - docs/**

forbidden_paths:
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/MX-T01/**
  - docs/milestones/closeout/**

acceptance:
  - Acceptance criterion.

required_evidence:
  verifier: not_applicable
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - acceptance unclear
```

## Evidence

Evidence lives under:

```text
docs/milestones/evidence/<task_id>/
```

## Closeout

Closeout lives under:

```text
docs/milestones/closeout/
```
