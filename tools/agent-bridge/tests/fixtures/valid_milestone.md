# Valid Milestone

### FX-T01: Valid task

```yaml task-contract
schema_version: 1
task_id: FX-T01
title: Valid task
canonical_owner: repo-doc
revision: 1
mode: direct
risk: low
lifecycle_status: ready
allowed_paths:
  - docs/**
forbidden_paths:
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**
managed_artifact_paths:
  - docs/milestones/evidence/FX-T01/**
  - docs/milestones/closeout/**
acceptance:
  - Valid task parses.
required_evidence:
  verifier: not_applicable
  reviewer: not_applicable
  functional_test: not_applicable
backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null
stop_conditions:
  - none
```
