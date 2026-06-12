#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MILESTONE = ROOT / "docs/milestones/M1.md"
EVIDENCE_ROOT = ROOT / "docs/milestones/evidence"
CLOSEOUT_ROOT = ROOT / "docs/milestones/closeout"

REQUIRED_FIELDS = [
    "schema_version",
    "task_id",
    "title",
    "canonical_owner",
    "revision",
    "mode",
    "risk",
    "lifecycle_status",
    "allowed_paths",
    "forbidden_paths",
    "managed_artifact_paths",
    "acceptance",
    "required_evidence",
    "backend_refs",
    "stop_conditions",
]

ENUMS = {
    "canonical_owner": {"repo-doc"},
    "mode": {"direct", "subagent", "borderline"},
    "risk": {"low", "medium", "high"},
    "lifecycle_status": {
        "proposed",
        "ready",
        "in_progress",
        "blocked",
        "reviewing",
        "verifying",
        "closed",
    },
}

EVIDENCE_VALUES = {"required", "not_applicable"}
FUNCTIONAL_TEST_LEVELS = {"FT-L0", "FT-L1", "FT-L2", "FT-L3", "FT-L4"}
GATE_ACCEPTED = "accepted"
GATE_FAILED = "failed"
GATE_INCONCLUSIVE = "inconclusive"
GITHUB_EVIDENCE_FILES = {
    "pr": "github-pr.yaml",
    "ci": "github-ci.yaml",
    "reviews": "github-reviews.yaml",
    "branch_protection": "github-branch-protection.yaml",
}
ISSUE_EVIDENCE_FILES = {
    "issue": "github-issue.yaml",
    "issue_comment": "github-issue-comment.yaml",
    "sync_report": "issue-sync-report.yaml",
}
TOKEN_KEY_RE = re.compile(r"(token|authorization|cookie|password|secret)", re.IGNORECASE)
TOKEN_VALUE_RE = re.compile(r"(gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|Bearer\s+[A-Za-z0-9._-]+)")
PROMPT_ROLES = {
    "orchestrator",
    "builder",
    "test-builder",
    "verifier",
    "reviewer",
    "functional-tester",
    "closeout",
}
DEFAULT_PHASE_NON_GOALS = [
    "Multica integration",
    "GitHub Issue sync",
    "GitHub Issue as canonical task source",
    "GitLab integration",
    "dashboard",
    "auto-merge",
    "model API calls",
    "autonomous long-running loops",
    "worker metrics routing",
    "bidirectional sync",
    "production secret handling",
    "VPN/internal network automation",
]


class BridgeError(Exception):
    pass


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def result_exit(result: str, tool_error: bool = False) -> int:
    if tool_error:
        return 3
    if result in {"valid", "pass", GATE_ACCEPTED}:
        return 0
    if result in {"invalid", "fail", GATE_FAILED}:
        return 1
    if result == GATE_INCONCLUSIVE:
        return 2
    return 3


def emit(payload: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload.get("result", "unknown"))
        for reason in payload.get("reasons", []):
            code = reason.get("code", "reason")
            message = reason.get("message", "")
            extra = reason.get("path") or reason.get("field") or reason.get("task_id") or ""
            suffix = f" ({extra})" if extra else ""
            print(f"- {code}{suffix}: {message}")
    return result_exit(payload.get("result", "tool_error"), payload.get("tool_error", False))


def parse_contracts(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path.exists():
        return [], [{"code": "missing_milestone", "message": f"{rel(path)} does not exist"}]
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"```yaml task-contract\n(.*?)\n```", text, flags=re.DOTALL)
    tasks: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for idx, block in enumerate(blocks, start=1):
        try:
            data = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            errors.append({"code": "invalid_yaml", "block": idx, "message": str(exc)})
            continue
        if not isinstance(data, dict):
            errors.append({"code": "invalid_contract", "block": idx, "message": "Contract is not a YAML mapping."})
            continue
        data["_block_index"] = idx
        tasks.append(data)
    if not blocks:
        errors.append({"code": "no_task_contracts", "message": "No fenced yaml task-contract blocks found."})
    return tasks, errors


def validate_task(task: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    task_id = task.get("task_id", f"block-{task.get('_block_index', '?')}")
    for field in REQUIRED_FIELDS:
        if field not in task:
            errors.append({"task_id": task_id, "field": field, "code": "missing_required_field", "message": f"Missing {field}."})
    for field, allowed in ENUMS.items():
        if field in task and task[field] not in allowed:
            errors.append({"task_id": task_id, "field": field, "code": "invalid_enum", "message": f"{field} must be one of {sorted(allowed)}."})
    if task.get("lifecycle_status") == "done":
        errors.append({"task_id": task_id, "field": "lifecycle_status", "code": "done_status_forbidden", "message": "Do not use done."})
    if task.get("schema_version") != 1:
        errors.append({"task_id": task_id, "field": "schema_version", "code": "unsupported_schema_version", "message": "Only schema_version 1 is supported."})
    if not isinstance(task.get("revision"), int) or task.get("revision", 0) < 1:
        errors.append({"task_id": task_id, "field": "revision", "code": "invalid_revision", "message": "revision must be a positive integer."})
    for field in ["allowed_paths", "forbidden_paths", "managed_artifact_paths", "acceptance", "stop_conditions"]:
        if field in task and not isinstance(task[field], list):
            errors.append({"task_id": task_id, "field": field, "code": "invalid_type", "message": f"{field} must be a list."})
    if isinstance(task.get("acceptance"), list) and not task["acceptance"]:
        errors.append({"task_id": task_id, "field": "acceptance", "code": "empty_acceptance", "message": "acceptance must not be empty."})
    required_evidence = task.get("required_evidence")
    if isinstance(required_evidence, dict):
        for key in ["verifier", "reviewer", "functional_test"]:
            value = required_evidence.get(key)
            if value not in EVIDENCE_VALUES:
                errors.append({"task_id": task_id, "field": f"required_evidence.{key}", "code": "invalid_evidence_requirement", "message": f"{key} must be required or not_applicable."})
    elif "required_evidence" in task:
        errors.append({"task_id": task_id, "field": "required_evidence", "code": "invalid_type", "message": "required_evidence must be a mapping."})
    if "backend_refs" in task and not isinstance(task["backend_refs"], dict):
        errors.append({"task_id": task_id, "field": "backend_refs", "code": "invalid_type", "message": "backend_refs must be a mapping."})
    for field in ["allowed_paths", "forbidden_paths", "managed_artifact_paths"]:
        for pattern in task.get(field, []) if isinstance(task.get(field), list) else []:
            if not isinstance(pattern, str) or pattern.startswith("/") or ".." in Path(pattern).parts:
                errors.append({"task_id": task_id, "field": field, "code": "invalid_path_pattern", "message": f"Invalid repo-relative path pattern: {pattern}"})
    return errors


def load_validated_tasks(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks, errors = parse_contracts(path)
    seen: dict[str, int] = {}
    for task in tasks:
        errors.extend(validate_task(task))
        task_id = task.get("task_id")
        if isinstance(task_id, str):
            if task_id in seen:
                errors.append({"task_id": task_id, "code": "duplicate_task_id", "message": f"Duplicate task_id also seen in block {seen[task_id]}."})
            seen[task_id] = task.get("_block_index", 0)
    return tasks, errors


def find_task(task_id: str, milestone: Path = DEFAULT_MILESTONE) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    tasks, errors = load_validated_tasks(milestone)
    if errors:
        return None, errors
    for task in tasks:
        if task.get("task_id") == task_id:
            return task, []
    return None, [{"code": "task_not_found", "task_id": task_id, "message": f"{task_id} not found in {rel(milestone)}."}]


def resolve_milestone(value: str | None, task_id: str | None = None) -> Path:
    if value and re.fullmatch(r"M\d+", value):
        return (ROOT / f"docs/milestones/{value}.md").resolve()
    if (
        task_id
        and (value is None or Path(value).resolve() == DEFAULT_MILESTONE)
        and (match := re.match(r"(M\d+)-", task_id))
    ):
        candidate = ROOT / f"docs/milestones/{match.group(1)}.md"
        if candidate.exists():
            return candidate.resolve()
    return Path(value or DEFAULT_MILESTONE).resolve()


def matches(pattern: str, path: str) -> bool:
    pattern = pattern.strip("/")
    path = path.strip("/")
    if pattern == "**":
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatch(path, pattern)


def any_match(patterns: list[str], path: str) -> bool:
    return any(matches(pattern, path) for pattern in patterns)


def run_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        raise BridgeError(exc.output.strip() or str(exc)) from exc


def git_commit_exists(ref: str) -> bool:
    try:
        run_git(["rev-parse", "--verify", f"{ref}^{{commit}}"])
    except BridgeError:
        return False
    return True


def current_branch() -> str | None:
    try:
        return run_git(["branch", "--show-current"]).strip() or None
    except BridgeError:
        return None


def parse_name_status(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            paths.extend(parts[1:3])
        else:
            paths.extend(parts[1:])
    return sorted(set(path for path in paths if path))


def changed_paths(base: str | None, head: str | None, worktree: bool) -> list[str]:
    if worktree:
        output = run_git(["diff", "--name-status", "--find-renames", "HEAD"])
        paths = parse_name_status(output)
        untracked = run_git(["ls-files", "--others", "--exclude-standard"]).splitlines()
        return sorted(set(paths + [p for p in untracked if p]))
    if base and head:
        return parse_name_status(run_git(["diff", "--name-status", "--find-renames", base, head]))
    raise BridgeError("Provide --worktree or both --base and --head.")


def changed_paths_from_source(source: dict[str, Any]) -> tuple[list[str] | None, dict[str, Any] | None]:
    mode = source.get("mode")
    include_paths = source.get("include_paths")
    if include_paths is not None and not isinstance(include_paths, list):
        return None, {"code": "invalid_path_policy_source", "message": "source.include_paths must be a list when present."}
    try:
        if mode == "worktree":
            paths = changed_paths(None, None, True)
            if include_paths:
                paths = [path for path in paths if any_match([str(item) for item in include_paths], path)]
            return paths, None
        if mode == "git_range":
            base = source.get("base_sha") or source.get("base")
            head = source.get("head_sha") or source.get("head")
            if not base or not head:
                return None, {"code": "invalid_path_policy_source", "message": "git_range source requires base_sha/head_sha or base/head."}
            if not git_commit_exists(str(base)):
                return None, {"code": "invalid_base_sha", "message": f"base_sha does not resolve: {base}"}
            if not git_commit_exists(str(head)):
                return None, {"code": "invalid_head_sha", "message": f"head_sha does not resolve: {head}"}
            paths = changed_paths(str(base), str(head), False)
            if include_paths:
                paths = [path for path in paths if any_match([str(item) for item in include_paths], path)]
            return paths, None
    except BridgeError as exc:
        return None, {"code": "path_policy_source_unavailable", "message": str(exc)}
    return None, {"code": "invalid_path_policy_source", "message": "source.mode must be worktree or git_range."}


def diff_check_payload(task: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    allowed = task.get("allowed_paths", [])
    forbidden = task.get("forbidden_paths", [])
    managed = task.get("managed_artifact_paths", [])
    violations = []
    for path in paths:
        if any_match(forbidden, path):
            violations.append({"code": "forbidden_path_changed", "path": path, "message": "Changed file is under forbidden_paths."})
            continue
        if not any_match(allowed + managed, path):
            violations.append({"code": "outside_allowed_paths", "path": path, "message": "Changed file is outside allowed_paths."})
    result = "fail" if violations else "pass"
    return {"result": result, "task_id": task["task_id"], "changed_files": paths, "reasons": violations}


def read_yaml(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not path.exists():
        return None, {"code": "missing_evidence", "path": rel(path), "message": f"{rel(path)} is missing."}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return None, {"code": "invalid_yaml", "path": rel(path), "message": str(exc)}
    if not isinstance(data, dict):
        return None, {"code": "invalid_evidence", "path": rel(path), "message": "Evidence is not a YAML mapping."}
    return data, None


def milestone_non_goals(milestone: Path) -> list[str]:
    if not milestone.exists():
        return DEFAULT_PHASE_NON_GOALS
    text = milestone.read_text(encoding="utf-8")
    match = re.search(r"^## Non-Goals\s*\n(?P<body>.*?)(?=^## |\Z)", text, flags=re.DOTALL | re.MULTILINE)
    if not match:
        return DEFAULT_PHASE_NON_GOALS
    items = []
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items or DEFAULT_PHASE_NON_GOALS


def read_evidence(task_id: str, filename: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    path = evidence_dir(task_id) / filename
    data, error = read_yaml(path)
    if error:
        return None, error
    assert data is not None
    if data.get("schema_version") != 1:
        return None, {"code": "invalid_evidence_schema_version", "path": rel(path), "message": "Evidence schema_version must be 1."}
    if data.get("task_id") != task_id:
        return None, {"code": "evidence_task_id_mismatch", "path": rel(path), "message": f"Evidence task_id must be {task_id}."}
    return data, None


def scrub_secret_values(value: Any) -> Any:
    if isinstance(value, dict):
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            if TOKEN_KEY_RE.search(str(key)):
                scrubbed[key] = "[REDACTED]"
            else:
                scrubbed[key] = scrub_secret_values(item)
        return scrubbed
    if isinstance(value, list):
        return [scrub_secret_values(item) for item in value]
    if isinstance(value, str):
        return TOKEN_VALUE_RE.sub("[REDACTED]", value)
    return value


def evidence_dir(task_id: str) -> Path:
    return EVIDENCE_ROOT / task_id


def check_verifier(task: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    task_id = task["task_id"]
    if task.get("required_evidence", {}).get("verifier") == "not_applicable":
        return "pass", []
    data, error = read_evidence(task_id, "verifier.yaml")
    if error:
        return GATE_INCONCLUSIVE, [error]
    verifier = data.get("verifier", data)
    commands = verifier.get("commands")
    if not isinstance(commands, list) or not commands:
        return GATE_INCONCLUSIVE, [{"code": "missing_verifier_commands", "message": "Verifier commands are required."}]
    reasons = []
    for index, command in enumerate(commands):
        if not isinstance(command, dict) or not command.get("command"):
            reasons.append({"code": "missing_command", "message": f"Verifier command {index} is missing command text."})
        if "exit_code" not in command:
            reasons.append({"code": "missing_exit_code", "message": f"Verifier command {index} is missing exit_code."})
        elif command.get("exit_code") != 0:
            return GATE_FAILED, [{"code": "verifier_command_failed", "message": f"Verifier command {index} exited non-zero."}]
    if reasons:
        return GATE_INCONCLUSIVE, reasons
    if verifier.get("conclusion") in {"fail", "failed"}:
        return GATE_FAILED, [{"code": "verifier_conclusion_failed", "message": "Verifier conclusion is failed."}]
    if verifier.get("conclusion") == GATE_INCONCLUSIVE:
        return GATE_INCONCLUSIVE, [{"code": "verifier_inconclusive", "message": "Verifier conclusion is inconclusive."}]
    return "pass", []


def check_reviewer(task: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    task_id = task["task_id"]
    if task.get("required_evidence", {}).get("reviewer") == "not_applicable":
        return "pass", []
    data, error = read_evidence(task_id, "reviewer.yaml")
    if error:
        return GATE_INCONCLUSIVE, [error]
    reviewer = data.get("reviewer")
    if not isinstance(reviewer, dict):
        return GATE_INCONCLUSIVE, [{"code": "missing_reviewer_block", "message": "reviewer evidence must include a reviewer mapping."}]
    conclusion = reviewer.get("conclusion")
    if conclusion not in {"pass", "fail", "failed", GATE_INCONCLUSIVE}:
        return GATE_INCONCLUSIVE, [{"code": "missing_reviewer_conclusion", "message": "reviewer.conclusion must be pass, fail, failed, or inconclusive."}]
    findings = reviewer.get("findings", [])
    if not isinstance(findings, list):
        return GATE_INCONCLUSIVE, [{"code": "invalid_reviewer_findings", "message": "reviewer.findings must be a list."}]
    for finding in findings:
        if not isinstance(finding, dict):
            return GATE_INCONCLUSIVE, [{"code": "invalid_reviewer_finding", "message": "Each reviewer finding must be a mapping."}]
        severity = str(finding.get("severity", "")).upper()
        if severity in {"P0", "P1"} and "status" not in finding:
            return GATE_INCONCLUSIVE, [{"code": "missing_reviewer_finding_status", "message": "P0/P1 reviewer findings must include status."}]
        status = str(finding.get("status", "open")).lower()
        if severity in {"P0", "P1"} and status not in {"resolved", "closed", "waived"}:
            return GATE_FAILED, [{"code": "open_blocking_reviewer_finding", "message": "Open P0/P1 reviewer finding blocks acceptance.", "finding": finding}]
    if conclusion in {"fail", "failed"}:
        return GATE_FAILED, [{"code": "reviewer_conclusion_failed", "message": "Reviewer conclusion is failed."}]
    if conclusion == GATE_INCONCLUSIVE:
        return GATE_INCONCLUSIVE, [{"code": "reviewer_inconclusive", "message": "Reviewer conclusion is inconclusive."}]
    return "pass", []


def check_functional(task: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    task_id = task["task_id"]
    if task.get("required_evidence", {}).get("functional_test") == "not_applicable":
        return "pass", []
    data, error = read_evidence(task_id, "functional-test.yaml")
    if error:
        return GATE_INCONCLUSIVE, [error]
    ft = data.get("functional_test", data)
    level = ft.get("level")
    if level is not None and level not in FUNCTIONAL_TEST_LEVELS:
        return GATE_INCONCLUSIVE, [{"code": "invalid_functional_test_level", "message": "functional_test.level must be FT-L0, FT-L1, FT-L2, FT-L3, or FT-L4."}]
    if ft.get("conclusion") in {"fail", "failed"}:
        return GATE_FAILED, [{"code": "functional_test_failed", "message": "Functional test failed."}]
    if ft.get("conclusion") != "pass":
        return GATE_INCONCLUSIVE, [{"code": "functional_test_not_passed", "message": "Functional test conclusion is not pass."}]
    return "pass", []


def check_path_policy(task: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    data, error = read_evidence(task["task_id"], "path-policy.yaml")
    if error:
        if error.get("code") == "missing_evidence":
            error["code"] = "missing_path_policy"
            error["message"] = "path-policy.yaml is required before gate acceptance."
        return GATE_INCONCLUSIVE, [error]
    result = data.get("result") or data.get("path_policy", {}).get("result")
    source = data.get("source")
    if not isinstance(source, dict) or source.get("mode") not in {"worktree", "git_range"}:
        return GATE_INCONCLUSIVE, [{"code": "missing_path_policy_source", "message": "path-policy.yaml must include source.mode as worktree or git_range."}]
    reasons = data.get("reasons", [])
    if not isinstance(reasons, list):
        return GATE_INCONCLUSIVE, [{"code": "invalid_path_policy_reasons", "message": "path-policy.reasons must be a list."}]
    changed_files = data.get("changed_files", [])
    if not isinstance(changed_files, list):
        return GATE_INCONCLUSIVE, [{"code": "invalid_path_policy_changed_files", "message": "path-policy.changed_files must be a list."}]
    blocking_reason_codes = {"forbidden_path_changed", "outside_allowed_paths"}
    blocking_reasons = [reason for reason in reasons if isinstance(reason, dict) and reason.get("code") in blocking_reason_codes]
    if blocking_reasons:
        return GATE_FAILED, blocking_reasons
    recomputed = diff_check_payload(task, [str(path) for path in changed_files])
    if recomputed["result"] == "fail":
        return GATE_FAILED, recomputed["reasons"]
    if result == "pass" and reasons:
        return GATE_INCONCLUSIVE, [{"code": "path_policy_pass_has_reasons", "message": "Passing path-policy evidence must not include violation reasons."}]
    if result != "pass" and result not in {"fail", GATE_FAILED, GATE_INCONCLUSIVE}:
        return GATE_INCONCLUSIVE, [{"code": "invalid_path_policy_result", "message": "path-policy.yaml must include result: pass, fail, failed, or inconclusive."}]
    source_paths, source_error = changed_paths_from_source(source)
    if source_error:
        return GATE_INCONCLUSIVE, [source_error]
    if sorted(set(str(path) for path in changed_files)) != sorted(set(source_paths or [])):
        return GATE_INCONCLUSIVE, [{"code": "path_policy_changed_files_mismatch", "message": "path-policy.changed_files must match the files changed by its source."}]
    base_ref = source.get("base_sha") or source.get("base")
    head_ref = source.get("head_sha") or source.get("head")
    if source.get("mode") == "git_range" and base_ref == head_ref and changed_files == []:
        return GATE_INCONCLUSIVE, [{"code": "empty_git_range_path_policy", "message": "Empty base/head path-policy evidence does not prove dirty worktree path safety."}]
    if result in {"fail", GATE_FAILED}:
        return GATE_FAILED, reasons or [{"code": "path_policy_failed", "message": "Path policy failed."}]
    if result == GATE_INCONCLUSIVE:
        return GATE_INCONCLUSIVE, reasons or [{"code": "path_policy_inconclusive", "message": "Path policy is inconclusive."}]
    return "pass", []


def check_blockers(task: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    data, error = read_evidence(task["task_id"], "blockers.yaml")
    if error:
        return "pass", []
    blockers = data.get("blockers", [])
    if not isinstance(blockers, list):
        return GATE_INCONCLUSIVE, [{"code": "invalid_blockers", "message": "blockers must be a list."}]
    for blocker in blockers:
        if not isinstance(blocker, dict):
            return GATE_INCONCLUSIVE, [{"code": "invalid_blocker", "message": "Each blocker must be a mapping."}]
        if "severity" not in blocker or "status" not in blocker:
            return GATE_INCONCLUSIVE, [{"code": "invalid_blocker_schema", "message": "Each blocker must include severity and status."}]
    open_blockers = [b for b in blockers if str(b.get("status", "open")).lower() not in {"resolved", "closed"}]
    if open_blockers:
        return GATE_FAILED, [{"code": "open_blocker", "message": "Open blocker exists.", "blocker": open_blockers[0]}]
    return "pass", []


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def github_collection(mode: str, network: bool, source: str) -> dict[str, Any]:
    return {"mode": mode, "network": network, "source": source}


def issue_collection(mode: str, network: bool, source: str) -> dict[str, Any]:
    return {"mode": mode, "network": network, "source": source}


def github_conclusion(value: Any) -> str:
    normalized = str(value or "").lower()
    if normalized in {"pass", "success", "successful", "accepted"}:
        return "pass"
    if normalized in {"fail", "failed", "failure", "cancel", "cancelled", "canceled", "timed_out", "action_required", "error"}:
        return "fail"
    if normalized in {"inconclusive", "pending", "queued", "in_progress", "unknown", "neutral", "skipped", "skipping"}:
        return "skipped" if normalized == "skipping" else normalized if normalized in {"neutral", "skipped"} else GATE_INCONCLUSIVE
    return GATE_INCONCLUSIVE


def normalize_github_fixture(task_id: str, raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = scrub_secret_values(raw)
    evidence: dict[str, dict[str, Any]] = {}
    collection = raw.get("collection")
    if not isinstance(collection, dict):
        collection = github_collection("fixture", False, "from-json")

    if isinstance(raw.get("github_pr"), dict):
        pr = dict(raw["github_pr"])
        pr.setdefault("queried_at", utc_now())
        pr.setdefault("conclusion", "pass")
        evidence["github-pr.yaml"] = {
            "schema_version": 1,
            "task_id": task_id,
            "source": "github",
            "collection": collection,
            "github_pr": pr,
        }

    if isinstance(raw.get("github_ci"), dict):
        ci = dict(raw["github_ci"])
        ci.setdefault("conclusion", infer_ci_conclusion(ci))
        evidence["github-ci.yaml"] = {
            "schema_version": 1,
            "task_id": task_id,
            "source": "github",
            "collection": collection,
            "github_ci": ci,
        }

    if isinstance(raw.get("github_reviews"), dict):
        reviews = dict(raw["github_reviews"])
        reviews.setdefault("conclusion", infer_review_conclusion(reviews))
        evidence["github-reviews.yaml"] = {
            "schema_version": 1,
            "task_id": task_id,
            "source": "github",
            "collection": collection,
            "github_reviews": reviews,
        }

    if isinstance(raw.get("github_branch_protection"), dict):
        protection = dict(raw["github_branch_protection"])
        protection.setdefault("conclusion", "pass" if protection.get("source_available") else GATE_INCONCLUSIVE)
        evidence["github-branch-protection.yaml"] = {
            "schema_version": 1,
            "task_id": task_id,
            "source": "github",
            "collection": collection,
            "github_branch_protection": protection,
        }
    return evidence


def infer_ci_conclusion(ci: dict[str, Any]) -> str:
    explicit = ci.get("conclusion")
    if explicit:
        conclusion = github_conclusion(explicit)
        if conclusion == "fail":
            return "fail"
        if conclusion == "pass":
            return "pass"
        if conclusion == GATE_INCONCLUSIVE:
            return GATE_INCONCLUSIVE
    checks: list[dict[str, Any]] = []
    for key in ["workflow_runs", "check_runs", "status_checks"]:
        value = ci.get(key, [])
        if isinstance(value, list):
            checks.extend(item for item in value if isinstance(item, dict))
    if not checks:
        return GATE_INCONCLUSIVE
    has_pending = False
    for check in checks:
        status = str(check.get("status", "")).lower()
        conclusion = github_conclusion(check.get("conclusion") or check.get("state"))
        if conclusion == "fail":
            return "fail"
        if status and status not in {"completed", "success"}:
            has_pending = True
        elif conclusion == GATE_INCONCLUSIVE:
            has_pending = True
    return GATE_INCONCLUSIVE if has_pending else "pass"


def infer_review_conclusion(reviews: dict[str, Any]) -> str:
    blocking = reviews.get("open_blocking_reviews", [])
    if isinstance(blocking, list) and blocking:
        return "fail"
    for review in reviews.get("reviews", []) if isinstance(reviews.get("reviews"), list) else []:
        if isinstance(review, dict) and str(review.get("state", "")).upper() == "CHANGES_REQUESTED":
            return "fail"
    return "pass"


def load_github_fixture(path: Path, task_id: str) -> tuple[dict[str, dict[str, Any]] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [{"code": "missing_github_fixture", "path": str(path), "message": "Fixture JSON does not exist."}]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [{"code": "invalid_github_fixture_json", "path": str(path), "message": str(exc)}]
    if not isinstance(raw, dict):
        return None, [{"code": "invalid_github_fixture", "path": str(path), "message": "Fixture must be a JSON object."}]
    evidence = normalize_github_fixture(task_id, raw)
    if not evidence:
        return None, [{"code": "empty_github_fixture", "path": str(path), "message": "Fixture did not contain recognized GitHub evidence sections."}]
    return evidence, []


def issue_marker(name: str, value: Any) -> str:
    return f"<!-- agent-bridge:{name} {value} -->"


def parse_issue_markers(body: str) -> dict[str, str | None]:
    markers: dict[str, str | None] = {}
    for key in ["task-id", "canonical-owner", "task-revision"]:
        match = re.search(rf"<!--\s*agent-bridge:{re.escape(key)}\s+(.+?)\s*-->", body or "")
        markers[key.replace("-", "_")] = match.group(1).strip() if match else None
    return markers


def issue_body_for_task(task: dict[str, Any]) -> str:
    acceptance = "\n".join(f"- {item}" for item in task.get("acceptance", []))
    allowed = yaml.safe_dump(task.get("allowed_paths", []), sort_keys=False).strip()
    forbidden = yaml.safe_dump(task.get("forbidden_paths", []), sort_keys=False).strip()
    return "\n".join(
        [
            issue_marker("task-id", task["task_id"]),
            issue_marker("canonical-owner", task.get("canonical_owner")),
            issue_marker("task-revision", task.get("revision")),
            "",
            "This GitHub Issue is an execution ticket mirror only.",
            "",
            "Canonical task scope remains in the repository milestone document.",
            "",
            f"Task: {task.get('title')}",
            f"Lifecycle: {task.get('lifecycle_status')}",
            f"Risk: {task.get('risk')}",
            "",
            "Acceptance:",
            acceptance or "- none",
            "",
            "Allowed paths:",
            "```yaml",
            allowed,
            "```",
            "",
            "Forbidden paths:",
            "```yaml",
            forbidden,
            "```",
        ]
    )


def normalize_issue_payload(task: dict[str, Any], issue: dict[str, Any], mode: str, source: str) -> dict[str, Any]:
    task_id = task["task_id"]
    body = str(issue.get("body") or "")
    markers = parse_issue_markers(body)
    task_revision = task.get("revision")
    issue_number = issue.get("number") or issue.get("issue_number")
    repository = issue.get("repository") or issue.get("repo")
    drift_reasons: list[dict[str, Any]] = []
    conclusion = "pass"
    if markers.get("task_id") != task_id:
        drift_reasons.append({"code": "issue_marker_task_id_mismatch", "message": "Issue body task_id marker does not match task."})
        conclusion = "fail"
    if markers.get("canonical_owner") != task.get("canonical_owner"):
        drift_reasons.append({"code": "issue_marker_canonical_owner_mismatch", "message": "Issue body canonical_owner marker does not match task."})
        conclusion = "fail"
    marker_revision = markers.get("task_revision")
    if marker_revision is None:
        drift_reasons.append({"code": "issue_marker_revision_missing", "message": "Issue body task revision marker is missing."})
        if conclusion != "fail":
            conclusion = GATE_INCONCLUSIVE
    elif str(marker_revision) != str(task_revision):
        drift_reasons.append({"code": "issue_revision_stale", "message": "Issue body task revision marker is stale."})
        if conclusion != "fail":
            conclusion = GATE_INCONCLUSIVE
    duplicate_numbers = issue.get("duplicate_issue_numbers", [])
    if isinstance(duplicate_numbers, list) and duplicate_numbers:
        drift_reasons.append({"code": "duplicate_issue_for_task_id", "message": "Multiple issues reference the same task_id."})
        conclusion = "fail"
    state = str(issue.get("state") or issue.get("issue_state") or "").lower()
    bridge_gate_result = issue.get("bridge_gate_result")
    if state == "closed" and bridge_gate_result != GATE_ACCEPTED:
        drift_reasons.append({"code": "issue_closed_without_bridge_acceptance", "message": "Issue is closed but Bridge gate is not accepted."})
        if conclusion != "fail":
            conclusion = GATE_INCONCLUSIVE
    return {
        "schema_version": 1,
        "task_id": task_id,
        "source": "github_issue",
        "repository": repository,
        "issue_number": issue_number,
        "issue_url": issue.get("url") or issue.get("issue_url"),
        "issue_state": state or None,
        "title": issue.get("title"),
        "labels": issue.get("labels", []),
        "milestone": issue.get("milestone"),
        "assignees": issue.get("assignees", []),
        "body_marker_task_id": markers.get("task_id"),
        "body_marker_canonical_owner": markers.get("canonical_owner"),
        "body_marker_task_revision": markers.get("task_revision"),
        "task_revision": task_revision,
        "sync_mode": mode,
        "fetched_at" if mode in {"live_read", "offline_fixture"} else "generated_at": utc_now(),
        "drift_detected": bool(drift_reasons),
        "drift_reasons": drift_reasons,
        "duplicate_issue_numbers": duplicate_numbers if isinstance(duplicate_numbers, list) else [],
        "conclusion": conclusion,
        "collection": issue_collection(mode, mode == "live_read", source),
    }


def load_issue_fixture(path: Path, task: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [{"code": "missing_issue_fixture", "path": str(path), "message": "Issue fixture JSON does not exist."}]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [{"code": "invalid_issue_fixture_json", "path": str(path), "message": str(exc)}]
    if not isinstance(raw, dict):
        return None, [{"code": "invalid_issue_fixture", "path": str(path), "message": "Issue fixture must be a JSON object."}]
    issue = raw.get("github_issue", raw)
    if not isinstance(issue, dict):
        return None, [{"code": "invalid_issue_fixture", "path": str(path), "message": "github_issue must be a JSON object."}]
    return normalize_issue_payload(task, scrub_secret_values(issue), "offline_fixture", "from-json"), []


def load_live_issue(task: dict[str, Any], repo: str, issue_number: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    payload, error = run_gh_json(["issue", "view", issue_number, "--repo", repo, "--json", "number,url,state,title,labels,milestone,assignees,body"])
    if error:
        return None, [error]
    if not isinstance(payload, dict):
        return None, [{"code": "invalid_github_issue_payload", "message": "gh issue view returned an unexpected payload."}]
    issue = {
        "repository": repo,
        "number": payload.get("number"),
        "url": payload.get("url"),
        "state": str(payload.get("state", "")).lower(),
        "title": payload.get("title"),
        "labels": [item.get("name") for item in payload.get("labels", []) if isinstance(item, dict)],
        "milestone": (payload.get("milestone") or {}).get("title") if isinstance(payload.get("milestone"), dict) else payload.get("milestone"),
        "assignees": [item.get("login") for item in payload.get("assignees", []) if isinstance(item, dict)],
        "body": payload.get("body"),
    }
    return normalize_issue_payload(task, scrub_secret_values(issue), "live_read", "gh-cli"), []


def issue_plan_payload(tasks: list[dict[str, Any]], milestone: Path, repo: str | None) -> dict[str, Any]:
    seen_task_ids: set[str] = set()
    seen_issues: dict[str, str] = {}
    items: list[dict[str, Any]] = []
    reasons: list[dict[str, Any]] = []
    for task in tasks:
        task_id = task.get("task_id")
        issue_ref = task.get("backend_refs", {}).get("github_issue")
        action = "create" if not issue_ref else "update"
        item = {"task_id": task_id, "title": task.get("title"), "github_issue": issue_ref, "action": action}
        if not issue_ref:
            item["reason"] = "missing_backend_ref"
        else:
            key = str(issue_ref)
            if key in seen_issues:
                reasons.append({"code": "duplicate_github_issue_ref", "task_id": task_id, "message": f"Also used by {seen_issues[key]}."})
            seen_issues[key] = str(task_id)
        if task_id in seen_task_ids:
            reasons.append({"code": "duplicate_task_id_conflict", "task_id": task_id, "message": "Duplicate task_id found in plan."})
        seen_task_ids.add(str(task_id))
        items.append(item)
    return {"result": "fail" if any(r["code"].startswith("duplicate") for r in reasons) else "pass", "milestone": rel(milestone), "repo": repo, "dry_run": True, "items": items, "reasons": reasons}


def issue_export_payload(task: dict[str, Any], repo: str | None, write: bool, issue_number: str | None = None) -> dict[str, Any]:
    task_id = task["task_id"]
    title = f"[{task_id}] {task.get('title')}"
    body = issue_body_for_task(task)
    payload = {
        "result": "pass",
        "task_id": task_id,
        "repo": repo,
        "dry_run": not write,
        "write": write,
        "idempotency_key": task_id,
        "issue_number": issue_number or task.get("backend_refs", {}).get("github_issue"),
        "title": title,
        "body": body,
        "markers": parse_issue_markers(body),
        "reasons": [],
    }
    if not write:
        return payload
    if not repo:
        return {**payload, "result": GATE_INCONCLUSIVE, "reasons": [{"code": "missing_repo", "message": "--repo is required for live write."}]}
    args = ["issue", "create", "--repo", repo, "--title", title, "--body", body]
    if payload["issue_number"]:
        args = ["issue", "edit", str(payload["issue_number"]), "--repo", repo, "--title", title, "--body", body]
    if not shutil.which("gh"):
        return {**payload, "result": GATE_INCONCLUSIVE, "reasons": [{"code": "gh_cli_unavailable", "message": "gh CLI is not available."}]}
    completed = subprocess.run(["gh", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr or completed.stdout or ""
        code = "github_auth_unavailable" if "auth" in stderr.lower() or "login" in stderr.lower() else "github_issue_write_failed"
        return {**payload, "result": GATE_INCONCLUSIVE, "reasons": [{"code": code, "message": f"gh issue write failed with exit code {completed.returncode}."}]}
    output = (completed.stdout or "").strip()
    if output.startswith("http"):
        payload["issue_url"] = output
    return payload


def issue_status_payload(task: dict[str, Any], repo: str | None, issue_number: str | None, fixture: str | None, write_evidence: bool) -> dict[str, Any]:
    if fixture:
        evidence, reasons = load_issue_fixture(Path(fixture), task)
    elif repo and issue_number:
        evidence, reasons = load_live_issue(task, repo, issue_number)
    else:
        evidence, reasons = None, [{"code": "missing_issue_input", "message": "Provide --from-json or both --repo and --issue."}]
    if reasons:
        return {"result": GATE_INCONCLUSIVE, "task_id": task["task_id"], "files": [], "reasons": reasons}
    assert evidence is not None
    files = []
    logical_path = logical_evidence_path(task["task_id"], "github-issue.yaml")
    if not any_match(task.get("managed_artifact_paths", []), logical_path):
        return {"result": "fail", "task_id": task["task_id"], "files": [], "reasons": [{"code": "outside_managed_artifact_paths", "path": logical_path, "message": "Issue evidence file is outside managed_artifact_paths."}]}
    if write_evidence:
        out_dir = evidence_dir(task["task_id"])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "github-issue.yaml").write_text(yaml.safe_dump(evidence, sort_keys=False), encoding="utf-8")
        action = "written"
    else:
        action = "would_write"
    files.append({"path": logical_path, "action": action})
    return {"result": evidence.get("conclusion", GATE_INCONCLUSIVE), "task_id": task["task_id"], "files": files, "issue": evidence, "reasons": evidence.get("drift_reasons", [])}


def issue_comment_payload(task: dict[str, Any], repo: str | None, issue_number: str | None, write: bool, write_evidence: bool = False) -> dict[str, Any]:
    gate = gate_payload(task)
    body = "\n".join(
        [
            f"<!-- agent-bridge:task-id {task['task_id']} -->",
            "<!-- agent-bridge:managed-comment gate-summary -->",
            f"Bridge gate result: {gate['result']}",
            "",
            "Checks:",
            yaml.safe_dump(gate.get("checks", {}), sort_keys=True).strip(),
        ]
    )
    payload = {"result": "pass", "task_id": task["task_id"], "dry_run": not write, "repo": repo, "issue_number": issue_number, "comment_body": body, "files": [], "reasons": []}
    if write:
        if not repo or not issue_number:
            payload = {**payload, "result": GATE_INCONCLUSIVE, "reasons": [{"code": "missing_issue_target", "message": "--repo and --issue are required for live write."}]}
        else:
            completed = subprocess.run(["gh", "issue", "comment", str(issue_number), "--repo", repo, "--body", body], cwd=ROOT, text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                payload = {**payload, "result": GATE_INCONCLUSIVE, "reasons": [{"code": "github_issue_comment_failed", "message": f"gh issue comment failed with exit code {completed.returncode}."}]}
    if write_evidence:
        logical_path = logical_evidence_path(task["task_id"], "github-issue-comment.yaml")
        if not any_match(task.get("managed_artifact_paths", []), logical_path):
            return {**payload, "result": "fail", "reasons": payload.get("reasons", []) + [{"code": "outside_managed_artifact_paths", "path": logical_path, "message": "Issue comment evidence file is outside managed_artifact_paths."}]}
        evidence = {
            "schema_version": 1,
            "task_id": task["task_id"],
            "source": "github_issue_comment",
            "collection": issue_collection("dry_run" if not write else "live_write", bool(write), "gh-cli" if write else "local"),
            "issue_number": issue_number,
            "repository": repo,
            "managed_comment": "gate-summary",
            "bridge_gate_result": gate["result"],
            "conclusion": "pass" if payload["result"] == "pass" else GATE_INCONCLUSIVE,
            "generated_at": utc_now(),
        }
        out_dir = evidence_dir(task["task_id"])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "github-issue-comment.yaml").write_text(yaml.safe_dump(evidence, sort_keys=False), encoding="utf-8")
        payload["files"].append({"path": logical_path, "action": "written"})
    return payload


def run_gh_json(args: list[str]) -> tuple[dict[str, Any] | list[Any] | None, dict[str, Any] | None]:
    if not shutil.which("gh"):
        return None, {"code": "gh_cli_unavailable", "message": "gh CLI is not available."}
    try:
        completed = subprocess.run(["gh", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    except OSError as exc:
        return None, {"code": "gh_cli_unavailable", "message": str(exc)}
    if completed.returncode != 0:
        stderr = completed.stderr or completed.stdout or ""
        code = "github_auth_unavailable" if "auth" in stderr.lower() or "login" in stderr.lower() else "github_read_failed"
        return None, {"code": code, "message": f"gh command failed with exit code {completed.returncode}."}
    try:
        return json.loads(completed.stdout or "{}"), None
    except json.JSONDecodeError as exc:
        return None, {"code": "invalid_gh_json", "message": str(exc)}


def load_live_github_evidence(task_id: str, repo: str, pr_number: str) -> tuple[dict[str, dict[str, Any]] | None, list[dict[str, Any]]]:
    collection = github_collection("gh", True, "gh-cli")
    pr_payload, pr_error = run_gh_json([
        "pr",
        "view",
        pr_number,
        "--repo",
        repo,
        "--json",
        "number,url,state,isDraft,baseRefName,headRefName,baseRefOid,headRefOid,mergeable,reviews",
    ])
    if pr_error:
        return None, [pr_error]
    if not isinstance(pr_payload, dict):
        return None, [{"code": "invalid_github_pr_payload", "message": "gh pr view returned an unexpected payload."}]
    pr = {
        "repo": repo,
        "pr_number": pr_payload.get("number"),
        "pr_url": pr_payload.get("url"),
        "state": str(pr_payload.get("state", "")).lower(),
        "draft": bool(pr_payload.get("isDraft")),
        "base_branch": pr_payload.get("baseRefName"),
        "head_branch": pr_payload.get("headRefName"),
        "base_sha": pr_payload.get("baseRefOid"),
        "head_sha": pr_payload.get("headRefOid"),
        "mergeable_state": pr_payload.get("mergeable"),
        "queried_at": utc_now(),
        "conclusion": GATE_INCONCLUSIVE if pr_payload.get("isDraft") else "pass",
    }
    evidence = {
        "github-pr.yaml": {
            "schema_version": 1,
            "task_id": task_id,
            "source": "github",
            "collection": collection,
            "github_pr": scrub_secret_values(pr),
        }
    }

    checks_payload, checks_error = run_gh_json(["pr", "checks", pr_number, "--repo", repo, "--json", "name,state,bucket,link,workflow"])
    if checks_error is None and isinstance(checks_payload, list):
        check_runs = [
            {
                "name": item.get("name"),
                "status": item.get("state"),
                "conclusion": item.get("bucket"),
                "url": item.get("link"),
                "workflow": item.get("workflow"),
            }
            for item in checks_payload
            if isinstance(item, dict)
        ]
        ci = {
            "repo": repo,
            "head_sha": pr.get("head_sha"),
            "required_checks_known": False,
            "workflow_runs": [],
            "check_runs": check_runs,
            "status_checks": [],
        }
    else:
        ci = {
            "repo": repo,
            "head_sha": pr.get("head_sha"),
            "required_checks_known": False,
            "workflow_runs": [],
            "check_runs": [],
            "status_checks": [],
            "reasons": [checks_error] if checks_error else [{"code": "github_checks_unavailable", "message": "GitHub checks were unavailable."}],
        }
    ci["conclusion"] = infer_ci_conclusion(ci)
    evidence["github-ci.yaml"] = {
        "schema_version": 1,
        "task_id": task_id,
        "source": "github",
        "collection": collection,
        "github_ci": scrub_secret_values(ci),
    }

    reviews_payload = pr_payload.get("reviews", [])
    if isinstance(reviews_payload, list):
        reviews = {
            "repo": repo,
            "pr_number": pr_payload.get("number"),
            "reviews": [
                {
                    "reviewer": (item.get("author") or {}).get("login") if isinstance(item.get("author"), dict) else item.get("author"),
                    "state": item.get("state"),
                    "commit_id": item.get("commit", {}).get("oid") if isinstance(item.get("commit"), dict) else item.get("commit_id"),
                    "submitted_at": item.get("submittedAt") or item.get("submitted_at"),
                }
                for item in reviews_payload
                if isinstance(item, dict)
            ],
            "open_blocking_reviews": [
                item for item in reviews_payload if isinstance(item, dict) and str(item.get("state", "")).upper() == "CHANGES_REQUESTED"
            ],
        }
        reviews["conclusion"] = infer_review_conclusion(reviews)
        evidence["github-reviews.yaml"] = {
            "schema_version": 1,
            "task_id": task_id,
            "source": "github",
            "collection": collection,
            "github_reviews": scrub_secret_values(reviews),
        }
    return evidence, []


def logical_evidence_path(task_id: str, filename: str) -> str:
    return f"docs/milestones/evidence/{task_id}/{filename}"


def github_evidence_payload(task: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    task_id = task["task_id"]
    reasons: list[dict[str, Any]] = []
    evidence: dict[str, dict[str, Any]] | None = None
    live = False
    if args.from_json:
        evidence, reasons = load_github_fixture(Path(args.from_json), task_id)
    else:
        if not args.repo or not args.pr:
            reasons = [{"code": "missing_github_input", "message": "Provide --from-json or both --repo and --pr."}]
        else:
            live = True
            evidence, reasons = load_live_github_evidence(task_id, args.repo, str(args.pr))
    if reasons:
        return {"result": GATE_INCONCLUSIVE, "task_id": task_id, "dry_run": not args.write_evidence or args.dry_run, "live": live, "files": [], "reasons": reasons}
    assert evidence is not None
    managed = task.get("managed_artifact_paths", [])
    files = []
    for filename, content in evidence.items():
        logical_path = logical_evidence_path(task_id, filename)
        if not any_match(managed, logical_path):
            reasons.append({"code": "outside_managed_artifact_paths", "path": logical_path, "message": "GitHub evidence file is outside managed_artifact_paths."})
            continue
        action = "would_write" if args.dry_run or not args.write_evidence else "written"
        if args.write_evidence and not args.dry_run:
            out_dir = evidence_dir(task_id)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / filename).write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
        files.append({"path": logical_path, "action": action})
    return {"result": "fail" if reasons else "pass", "task_id": task_id, "dry_run": args.dry_run or not args.write_evidence, "live": live, "files": files, "reasons": reasons}


def required_github_evidence(task: dict[str, Any]) -> list[str]:
    value = task.get("required_github_evidence")
    if isinstance(value, list):
        return [str(item) for item in value]
    github = task.get("github_evidence")
    if isinstance(github, dict) and isinstance(github.get("required"), list):
        return [str(item) for item in github["required"]]
    return []


def task_evidence_head_sha(task_id: str) -> tuple[str | None, dict[str, Any] | None]:
    data, error = read_evidence(task_id, "path-policy.yaml")
    if error:
        return None, error
    source = data.get("source")
    if not isinstance(source, dict):
        return None, {"code": "missing_path_policy_source", "message": "path-policy.yaml must include source for SHA consistency."}
    head = source.get("head_sha") or source.get("head")
    return str(head) if head else None, None


def check_github_evidence(task: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    required = required_github_evidence(task)
    if not required:
        return "pass", []
    task_id = task["task_id"]
    reasons: list[dict[str, Any]] = []
    result = "pass"
    loaded: dict[str, dict[str, Any]] = {}
    for item in required:
        filename = GITHUB_EVIDENCE_FILES.get(item)
        if not filename:
            reasons.append({"code": "unknown_required_github_evidence", "message": f"Unknown GitHub evidence requirement: {item}"})
            result = GATE_INCONCLUSIVE
            continue
        data, error = read_evidence(task_id, filename)
        if error:
            reasons.append({"code": f"missing_github_{item}_evidence", "message": f"{filename} is required.", "path": rel(evidence_dir(task_id) / filename)})
            result = GATE_INCONCLUSIVE
            continue
        if data.get("source") != "github":
            reasons.append({"code": "invalid_github_evidence_source", "message": f"{filename} must include source: github.", "path": rel(evidence_dir(task_id) / filename)})
            result = GATE_INCONCLUSIVE
            continue
        loaded[item] = data

    pr_head = None
    if "pr" in loaded:
        pr = loaded["pr"].get("github_pr", {})
        if not isinstance(pr, dict):
            reasons.append({"code": "invalid_github_pr_evidence", "message": "github-pr.yaml must include github_pr mapping."})
            result = GATE_INCONCLUSIVE
        else:
            pr_head = pr.get("head_sha")
            if not pr.get("repo") or not pr.get("pr_number") or not pr.get("pr_url") or not pr_head:
                reasons.append({"code": "missing_github_pr_fields", "message": "PR evidence is missing repo, pr_number, pr_url, or head_sha."})
                result = GATE_INCONCLUSIVE
            if pr.get("draft"):
                reasons.append({"code": "github_pr_draft", "message": "PR is draft."})
                result = GATE_INCONCLUSIVE
            state = str(pr.get("state", "")).lower()
            if state == "closed" and not pr.get("merged", False):
                reasons.append({"code": "github_pr_closed_unmerged", "message": "PR is closed without merge."})
                result = GATE_FAILED

    if "ci" in loaded:
        ci = loaded["ci"].get("github_ci", {})
        if not isinstance(ci, dict):
            reasons.append({"code": "invalid_github_ci_evidence", "message": "github-ci.yaml must include github_ci mapping."})
            result = GATE_INCONCLUSIVE
        else:
            ci_head = ci.get("head_sha")
            if pr_head and ci_head and str(ci_head) != str(pr_head):
                reasons.append({"code": "github_ci_head_sha_mismatch", "message": "CI head_sha does not match PR head_sha."})
                result = GATE_FAILED
            conclusion = infer_ci_conclusion(ci)
            if conclusion == "fail":
                reasons.append({"code": "github_ci_failed", "message": "Required GitHub CI/check evidence failed."})
                result = GATE_FAILED
            elif conclusion == GATE_INCONCLUSIVE:
                reasons.append({"code": "github_ci_inconclusive", "message": "GitHub CI/check evidence is pending, missing, or unknown."})
                if result != GATE_FAILED:
                    result = GATE_INCONCLUSIVE

    if "reviews" in loaded:
        reviews = loaded["reviews"].get("github_reviews", {})
        if not isinstance(reviews, dict):
            reasons.append({"code": "invalid_github_reviews_evidence", "message": "github-reviews.yaml must include github_reviews mapping."})
            result = GATE_INCONCLUSIVE
        else:
            conclusion = infer_review_conclusion(reviews)
            if conclusion == "fail":
                reasons.append({"code": "github_reviews_blocking", "message": "Open blocking PR review exists."})
                result = GATE_FAILED

    if "branch_protection" in loaded:
        protection = loaded["branch_protection"].get("github_branch_protection", {})
        if not isinstance(protection, dict) or not protection.get("source_available"):
            reasons.append({"code": "github_branch_protection_unavailable", "message": "Branch protection evidence is unavailable."})
            if result != GATE_FAILED:
                result = GATE_INCONCLUSIVE

    require_sha = bool(task.get("github_sha_consistency_required")) or ("pr" in loaded and "ci" in loaded)
    if require_sha and pr_head:
        task_head, head_error = task_evidence_head_sha(task_id)
        if head_error or not task_head:
            reasons.append({"code": "task_head_sha_unavailable", "message": "Task evidence head_sha is unavailable for GitHub SHA consistency."})
            if result != GATE_FAILED:
                result = GATE_INCONCLUSIVE
        elif str(task_head) != str(pr_head):
            reasons.append({"code": "github_pr_head_sha_mismatch", "message": "PR head_sha does not match task evidence head_sha."})
            result = GATE_FAILED
    return result, reasons


def required_issue_evidence(task: dict[str, Any]) -> list[str]:
    value = task.get("required_issue_evidence")
    if isinstance(value, list):
        return [str(item) for item in value]
    issue = task.get("issue_evidence")
    if isinstance(issue, dict) and isinstance(issue.get("required"), list):
        return [str(item) for item in issue["required"]]
    return []


def check_issue_evidence(task: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    required = required_issue_evidence(task)
    if not required:
        return "pass", []
    task_id = task["task_id"]
    reasons: list[dict[str, Any]] = []
    result = "pass"
    for item in required:
        filename = ISSUE_EVIDENCE_FILES.get(item)
        if not filename:
            reasons.append({"code": "unknown_required_issue_evidence", "message": f"Unknown issue evidence requirement: {item}"})
            result = GATE_INCONCLUSIVE
            continue
        data, error = read_evidence(task_id, filename)
        if error:
            reasons.append({"code": f"missing_issue_{item}_evidence", "message": f"{filename} is required.", "path": rel(evidence_dir(task_id) / filename)})
            result = GATE_INCONCLUSIVE
            continue
        if item == "issue":
            if data.get("source") != "github_issue":
                reasons.append({"code": "invalid_issue_evidence_source", "message": "github-issue.yaml must include source: github_issue."})
                result = GATE_INCONCLUSIVE
            if data.get("body_marker_task_id") != task_id:
                reasons.append({"code": "issue_marker_task_id_mismatch", "message": "Issue body task_id marker does not match task."})
                result = GATE_FAILED
            if data.get("body_marker_canonical_owner") != task.get("canonical_owner"):
                reasons.append({"code": "issue_marker_canonical_owner_mismatch", "message": "Issue body canonical_owner marker does not match task."})
                result = GATE_FAILED
            if str(data.get("body_marker_task_revision")) != str(task.get("revision")):
                reasons.append({"code": "issue_revision_stale", "message": "Issue body task revision marker is missing or stale."})
                if result != GATE_FAILED:
                    result = GATE_INCONCLUSIVE
            duplicates = data.get("duplicate_issue_numbers", [])
            if isinstance(duplicates, list) and duplicates:
                reasons.append({"code": "duplicate_issue_for_task_id", "message": "Multiple issues reference the same task_id."})
                result = GATE_FAILED
            conclusion = data.get("conclusion")
            if conclusion in {"fail", "failed"}:
                for reason in data.get("drift_reasons", []) if isinstance(data.get("drift_reasons"), list) else []:
                    if isinstance(reason, dict):
                        reasons.append(reason)
                result = GATE_FAILED
            elif conclusion == GATE_INCONCLUSIVE:
                for reason in data.get("drift_reasons", []) if isinstance(data.get("drift_reasons"), list) else []:
                    if isinstance(reason, dict):
                        reasons.append(reason)
                if result != GATE_FAILED:
                    result = GATE_INCONCLUSIVE
        elif item == "issue_comment":
            if data.get("source") != "github_issue_comment":
                reasons.append({"code": "invalid_issue_comment_evidence_source", "message": "github-issue-comment.yaml must include source: github_issue_comment."})
                result = GATE_INCONCLUSIVE
            if data.get("conclusion") in {"fail", "failed"}:
                reasons.append({"code": "issue_comment_failed", "message": "GitHub Issue comment evidence failed."})
                result = GATE_FAILED
        elif item == "sync_report":
            conclusion = data.get("conclusion")
            if conclusion in {"fail", "failed"}:
                reasons.append({"code": "issue_sync_report_failed", "message": "Issue sync report failed."})
                result = GATE_FAILED
            elif conclusion != "pass":
                reasons.append({"code": "issue_sync_report_inconclusive", "message": "Issue sync report is not passing."})
                if result != GATE_FAILED:
                    result = GATE_INCONCLUSIVE
    return result, reasons


def gate_payload(task: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "path_policy": check_path_policy(task),
        "verifier": check_verifier(task),
        "reviewer": check_reviewer(task),
        "functional_test": check_functional(task),
        "blockers": check_blockers(task),
        "github_evidence": check_github_evidence(task),
        "issue_evidence": check_issue_evidence(task),
    }
    reasons: list[dict[str, Any]] = []
    result = GATE_ACCEPTED
    for name, (check_result, check_reasons) in checks.items():
        for reason in check_reasons:
            reason.setdefault("check", name)
        reasons.extend(check_reasons)
        if check_result == GATE_FAILED:
            result = GATE_FAILED
        elif check_result == GATE_INCONCLUSIVE and result != GATE_FAILED:
            result = GATE_INCONCLUSIVE
    return {"result": result, "task_id": task["task_id"], "checks": {k: v[0] for k, v in checks.items()}, "reasons": reasons}


def command_validate(args: argparse.Namespace) -> int:
    path = resolve_milestone(args.milestone)
    tasks, errors = load_validated_tasks(path)
    payload = {
        "result": "invalid" if errors else "valid",
        "milestone": rel(path) if path.is_relative_to(ROOT) else str(path),
        "tasks_checked": len(tasks),
        "reasons": errors,
    }
    return emit(payload, args.json)


def command_diff_check(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, resolve_milestone(args.milestone, args.task))
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    try:
        paths = changed_paths(args.base, args.head, args.worktree)
        payload = diff_check_payload(task, paths)
        payload["source"] = (
            {"mode": "worktree"}
            if args.worktree
            else {"mode": "git_range", "base_sha": args.base, "head_sha": args.head, "base": args.base, "head": args.head}
        )
        if args.include_path:
            payload["source"]["include_paths"] = args.include_path
            payload["changed_files"] = [path for path in payload["changed_files"] if any_match(args.include_path, path)]
            payload = diff_check_payload(task, payload["changed_files"]) | {"source": payload["source"]}
    except BridgeError as exc:
        payload = {"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": [{"code": "git_state_unavailable", "message": str(exc)}]}
    if args.write_evidence:
        out_dir = evidence_dir(args.task)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "path-policy.yaml").write_text(yaml.safe_dump({"schema_version": 1, "task_id": args.task, **payload}, sort_keys=False), encoding="utf-8")
    return emit(payload, args.json)


def task_info_payload(task: dict[str, Any], milestone: Path) -> dict[str, Any]:
    fields = [
        "task_id",
        "title",
        "canonical_owner",
        "revision",
        "mode",
        "risk",
        "lifecycle_status",
        "allowed_paths",
        "forbidden_paths",
        "managed_artifact_paths",
        "acceptance",
        "required_evidence",
        "backend_refs",
        "stop_conditions",
    ]
    return {
        "result": "pass",
        "milestone": rel(milestone) if milestone.is_relative_to(ROOT) else str(milestone),
        "task": {field: task.get(field) for field in fields},
        "reasons": [],
    }


def command_task_info(args: argparse.Namespace) -> int:
    milestone = resolve_milestone(args.milestone, args.task)
    task, errors = find_task(args.task, milestone)
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    payload = task_info_payload(task, milestone)
    if args.json:
        return emit(payload, True)
    task_data = payload["task"]
    print(f"{task_data['task_id']}: {task_data['title']}")
    print(f"milestone: {payload['milestone']}")
    print(f"mode: {task_data['mode']}")
    print(f"risk: {task_data['risk']}")
    print(f"lifecycle_status: {task_data['lifecycle_status']}")
    print("allowed_paths:")
    for path in task_data.get("allowed_paths", []):
        print(f"- {path}")
    print("forbidden_paths:")
    for path in task_data.get("forbidden_paths", []):
        print(f"- {path}")
    print("required_evidence:")
    for key, value in task_data.get("required_evidence", {}).items():
        print(f"- {key}: {value}")
    print("stop_conditions:")
    for condition in task_data.get("stop_conditions", []):
        print(f"- {condition}")
    return 0


def evidence_skeletons(task: dict[str, Any]) -> dict[str, dict[str, Any]]:
    task_id = task["task_id"]
    required = task.get("required_evidence", {})
    skeletons: dict[str, dict[str, Any]] = {
        "path-policy.yaml": {
            "schema_version": 1,
            "task_id": task_id,
            "result": GATE_INCONCLUSIVE,
            "source": {"mode": "worktree"},
            "changed_files": [],
            "reasons": [{"code": "evidence_initialized", "message": "Skeleton only. Run diff-check to produce path-policy evidence."}],
        },
        "blockers.yaml": {"schema_version": 1, "task_id": task_id, "blockers": []},
    }
    if required.get("verifier") == "required":
        skeletons["verifier.yaml"] = {
            "schema_version": 1,
            "task_id": task_id,
            "verifier": {
                "commands": [],
                "conclusion": GATE_INCONCLUSIVE,
            },
        }
    if required.get("reviewer") == "required":
        skeletons["reviewer.yaml"] = {
            "schema_version": 1,
            "task_id": task_id,
            "reviewer": {
                "findings": [],
                "conclusion": GATE_INCONCLUSIVE,
            },
        }
    if required.get("functional_test") == "required":
        skeletons["functional-test.yaml"] = {
            "schema_version": 1,
            "task_id": task_id,
            "functional_test": {
                "level": None,
                "conclusion": GATE_INCONCLUSIVE,
            },
        }
    return skeletons


def evidence_init_payload(task: dict[str, Any], dry_run: bool, force: bool) -> dict[str, Any]:
    task_id = task["task_id"]
    out_dir = evidence_dir(task_id)
    managed = task.get("managed_artifact_paths", [])
    files = []
    reasons = []
    skeletons = evidence_skeletons(task)
    for filename, content in skeletons.items():
        path = out_dir / filename
        rel_path = rel(path)
        if not any_match(managed, rel_path):
            reasons.append({"code": "outside_managed_artifact_paths", "path": rel_path, "message": "Evidence file is outside managed_artifact_paths."})
            continue
        action = "would_create" if dry_run else "created"
        if path.exists() and not force:
            action = "exists"
        elif not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
        files.append({"path": rel_path, "action": action})
    result = "fail" if reasons else "pass"
    return {"result": result, "task_id": task_id, "dry_run": dry_run, "files": files, "reasons": reasons}


def command_evidence_init(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, resolve_milestone(args.milestone, args.task))
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    payload = evidence_init_payload(task, args.dry_run, args.force)
    if args.json:
        return emit(payload, True)
    print(payload["result"])
    for item in payload.get("files", []):
        print(f"- {item['action']}: {item['path']}")
    for reason in payload.get("reasons", []):
        print(f"- {reason.get('code')}: {reason.get('message')} ({reason.get('path')})")
    return result_exit(payload["result"])


def prompt_for_role(task: dict[str, Any], role: str, milestone: Path) -> str:
    task_id = task["task_id"]
    non_goal_lines = "\n".join(f"- {item}" for item in milestone_non_goals(milestone))
    common = f"""You are acting as {role} for task {task_id}.

Repository: {ROOT}
Milestone: {rel(milestone) if milestone.is_relative_to(ROOT) else milestone}
Task: {task.get('title')}
Mode: {task.get('mode')}
Risk: {task.get('risk')}
Lifecycle status: {task.get('lifecycle_status')}

Milestone docs are the canonical task source.
Do not treat chat summaries, model confidence, comments, branch names, or issue tracker status as final acceptance evidence.

Allowed paths:
{yaml.safe_dump(task.get('allowed_paths', []), sort_keys=False).strip()}

Forbidden paths:
{yaml.safe_dump(task.get('forbidden_paths', []), sort_keys=False).strip()}

Required evidence:
{yaml.safe_dump(task.get('required_evidence', {}), sort_keys=False).strip()}

Stop conditions:
{yaml.safe_dump(task.get('stop_conditions', []), sort_keys=False).strip()}

Phase 2 non-goals:
{non_goal_lines}
"""
    role_rules = {
        "orchestrator": "Plan role split, check evidence readiness, and never override hard gate rules.",
        "builder": "Implement only the requested task. Modify only allowed paths. Report changed files and commands.",
        "test-builder": "Add or update tests and fixtures only. Do not change production logic unless the task allows it.",
        "verifier": "Run commands and collect exit codes. Do not modify implementation code.",
        "reviewer": "Review the diff. Report concrete findings with severity, status, file, issue, and required action.",
        "functional-tester": "Validate user-observable behavior when applicable. Prefer black-box testing.",
        "closeout": "Generate closeout from evidence and git facts. Do not mark failed or inconclusive work as accepted.",
    }
    return common + "\nRole-specific instructions:\n" + role_rules[role] + "\n"


def command_prompt_pack(args: argparse.Namespace) -> int:
    milestone = resolve_milestone(args.milestone, args.task)
    task, errors = find_task(args.task, milestone)
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    prompt = prompt_for_role(task, args.role, milestone)
    payload = {"result": "pass", "task_id": args.task, "role": args.role, "prompt": prompt, "reasons": []}
    if args.json:
        return emit(payload, True)
    print(prompt)
    return 0


def command_github_evidence(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, resolve_milestone(args.milestone, args.task))
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    payload = github_evidence_payload(task, args)
    if args.json:
        return emit(payload, True)
    print(payload["result"])
    for item in payload.get("files", []):
        print(f"- {item['action']}: {item['path']}")
    for reason in payload.get("reasons", []):
        print(f"- {reason.get('code')}: {reason.get('message')}")
    return result_exit(payload["result"])


def command_issue_plan(args: argparse.Namespace) -> int:
    milestone = resolve_milestone(args.milestone)
    tasks, errors = load_validated_tasks(milestone)
    if errors:
        return emit({"result": GATE_INCONCLUSIVE, "milestone": rel(milestone), "reasons": errors}, args.json)
    payload = issue_plan_payload(tasks, milestone, args.repo)
    return emit(payload, args.json)


def command_issue_export(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, resolve_milestone(args.milestone, args.task))
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    payload = issue_export_payload(task, args.repo, args.write, args.issue)
    if args.json:
        return emit(payload, True)
    print(payload["result"])
    print(payload.get("title", ""))
    if payload.get("dry_run"):
        print(payload.get("body", ""))
    for reason in payload.get("reasons", []):
        print(f"- {reason.get('code')}: {reason.get('message')}")
    return result_exit(payload["result"])


def command_issue_status(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, resolve_milestone(args.milestone, args.task))
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    payload = issue_status_payload(task, args.repo, args.issue, args.from_json, args.write_evidence)
    if args.json:
        return emit(payload, True)
    print(payload["result"])
    for item in payload.get("files", []):
        print(f"- {item['action']}: {item['path']}")
    for reason in payload.get("reasons", []):
        print(f"- {reason.get('code')}: {reason.get('message')}")
    return result_exit(payload["result"])


def command_issue_comment(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, resolve_milestone(args.milestone, args.task))
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    payload = issue_comment_payload(task, args.repo, args.issue, args.write, args.write_evidence)
    if args.json:
        return emit(payload, True)
    print(payload["result"])
    if payload.get("dry_run"):
        print(payload.get("comment_body", ""))
    for reason in payload.get("reasons", []):
        print(f"- {reason.get('code')}: {reason.get('message')}")
    return result_exit(payload["result"])


def command_gate(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, resolve_milestone(args.milestone, args.task))
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    payload = gate_payload(task)
    if args.write_report:
        out_dir = evidence_dir(args.task)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "gate-report.yaml").write_text(yaml.safe_dump({"schema_version": 1, **payload}, sort_keys=False), encoding="utf-8")
    return emit(payload, args.json)


def summarize_evidence(task: dict[str, Any]) -> tuple[list[str], list[str]]:
    task_id = task["task_id"]
    directory = evidence_dir(task_id)
    evidence_lines: list[str] = []
    changed_files: list[str] = []
    required = task.get("required_evidence", {})
    evidence_files = [
        ("path-policy.yaml", "result", None),
        ("verifier.yaml", "verifier.conclusion", "verifier"),
        ("reviewer.yaml", "reviewer.conclusion", "reviewer"),
        ("functional-test.yaml", "functional_test.conclusion", "functional_test"),
        ("blockers.yaml", "blockers", None),
        ("gate-report.yaml", "result", None),
    ]
    for filename, key, requirement_key in evidence_files:
        path = directory / filename
        if filename == "path-policy.yaml":
            check_result, check_reasons = check_path_policy(task)
            reason_codes = ",".join(reason.get("code", "reason") for reason in check_reasons)
            suffix = f" ({reason_codes})" if reason_codes else ""
            evidence_lines.append(f"- {filename}: {check_result}{suffix}")
            data, _ = read_yaml(path)
            if data:
                changed = data.get("changed_files", [])
                if isinstance(changed, list):
                    changed_files = [str(item) for item in changed]
            continue
        data, error = read_evidence(task_id, filename)
        if error:
            if requirement_key and required.get(requirement_key) == "not_applicable":
                evidence_lines.append(f"- {filename}: not_applicable")
            else:
                evidence_lines.append(f"- {filename}: {error.get('code', 'invalid')}")
            continue
        value: Any = None
        if key == "verifier.conclusion":
            value = data.get("verifier", {}).get("conclusion")
        elif key == "reviewer.conclusion":
            value = data.get("reviewer", {}).get("conclusion")
        elif key == "functional_test.conclusion":
            value = data.get("functional_test", {}).get("conclusion")
        elif key == "blockers":
            blockers = data.get("blockers", [])
            value = f"{len(blockers)} recorded" if isinstance(blockers, list) else "invalid"
        else:
            value = data.get(key)
        evidence_lines.append(f"- {filename}: {value if value is not None else 'present'}")
        if filename == "path-policy.yaml":
            changed = data.get("changed_files", [])
            if isinstance(changed, list):
                changed_files = [str(item) for item in changed]
    return evidence_lines, changed_files


def summarize_github_evidence(task_id: str) -> list[str]:
    lines: list[str] = []
    pr_data, _ = read_evidence(task_id, "github-pr.yaml")
    if pr_data and isinstance(pr_data.get("github_pr"), dict):
        pr = pr_data["github_pr"]
        if pr.get("pr_url"):
            lines.append(f"- PR: {pr.get('pr_url')}")
        if pr.get("state"):
            lines.append(f"- PR state: {pr.get('state')}")
        if pr.get("head_sha"):
            lines.append(f"- PR head_sha: {pr.get('head_sha')}")
    ci_data, _ = read_evidence(task_id, "github-ci.yaml")
    if ci_data and isinstance(ci_data.get("github_ci"), dict):
        ci = ci_data["github_ci"]
        lines.append(f"- CI conclusion: {ci.get('conclusion', infer_ci_conclusion(ci))}")
        checks = []
        for key in ["workflow_runs", "check_runs", "status_checks"]:
            value = ci.get(key, [])
            if isinstance(value, list):
                checks.extend(item for item in value if isinstance(item, dict))
        for check in checks[:5]:
            name = check.get("name") or check.get("workflow") or "check"
            conclusion = check.get("conclusion") or check.get("status") or check.get("state") or "unknown"
            lines.append(f"- Check: {name} = {conclusion}")
    review_data, _ = read_evidence(task_id, "github-reviews.yaml")
    if review_data and isinstance(review_data.get("github_reviews"), dict):
        reviews = review_data["github_reviews"]
        review_items = reviews.get("reviews", [])
        count = len(review_items) if isinstance(review_items, list) else 0
        lines.append(f"- Review conclusion: {reviews.get('conclusion', infer_review_conclusion(reviews))}")
        lines.append(f"- Reviews recorded: {count}")
    protection_data, _ = read_evidence(task_id, "github-branch-protection.yaml")
    if protection_data and isinstance(protection_data.get("github_branch_protection"), dict):
        protection = protection_data["github_branch_protection"]
        lines.append(f"- Branch protection available: {bool(protection.get('source_available'))}")
    return lines


def summarize_issue_evidence(task_id: str) -> list[str]:
    lines: list[str] = []
    issue_data, _ = read_evidence(task_id, "github-issue.yaml")
    if issue_data:
        if issue_data.get("issue_url"):
            lines.append(f"- Issue: {issue_data.get('issue_url')}")
        if issue_data.get("issue_state"):
            lines.append(f"- Issue state: {issue_data.get('issue_state')}")
        if issue_data.get("body_marker_task_revision"):
            lines.append(f"- Issue task revision: {issue_data.get('body_marker_task_revision')}")
        lines.append(f"- Issue conclusion: {issue_data.get('conclusion', 'unknown')}")
        drift_reasons = issue_data.get("drift_reasons", [])
        if isinstance(drift_reasons, list) and drift_reasons:
            lines.append(f"- Issue drift reasons: {', '.join(str(item.get('code', 'reason')) for item in drift_reasons if isinstance(item, dict))}")
    comment_data, _ = read_evidence(task_id, "github-issue-comment.yaml")
    if comment_data:
        lines.append(f"- Issue comment conclusion: {comment_data.get('conclusion', 'present')}")
    sync_data, _ = read_evidence(task_id, "issue-sync-report.yaml")
    if sync_data:
        lines.append(f"- Issue sync report: {sync_data.get('conclusion', sync_data.get('result', 'present'))}")
    return lines


def closeout_block(task: dict[str, Any], gate: dict[str, Any], milestone: Path = DEFAULT_MILESTONE) -> str:
    task_id = task["task_id"]
    status = gate["result"]
    reasons = gate.get("reasons", [])
    reason_lines = "\n".join(f"- {r.get('code')}: {r.get('message', '')}" for r in reasons) or "- none"
    evidence_lines, changed_files = summarize_evidence(task)
    changed_file_lines = "\n".join(f"- {path}" for path in changed_files) or "- none"
    evidence_summary = "\n".join(evidence_lines) or "- none"
    github_summary = "\n".join(summarize_github_evidence(task_id)) or "- none"
    issue_summary = "\n".join(summarize_issue_evidence(task_id)) or "- none"
    branch = current_branch() or "unknown"
    source_lines = "- none"
    path_policy, _ = read_evidence(task_id, "path-policy.yaml")
    if path_policy and isinstance(path_policy.get("source"), dict):
        source = path_policy["source"]
        base = source.get("base_sha") or source.get("base")
        head = source.get("head_sha") or source.get("head")
        source_lines = "\n".join(
            f"- {line}" for line in [
                f"mode: {source.get('mode')}",
                f"base: {base}" if base else "",
                f"head: {head}" if head else "",
                f"branch: {branch}",
            ] if line
        )
    risk_lines = "- none" if status == GATE_ACCEPTED else reason_lines
    followup_lines = "- none" if status == GATE_ACCEPTED else "- resolve gate reasons and rerun agent-bridge gate"
    milestone_label = rel(milestone) if milestone.is_relative_to(ROOT) else str(milestone)
    resume_lines = "\n".join([
        f"- Read {milestone_label} for task {task_id}.",
        f"- Inspect docs/milestones/evidence/{task_id}/.",
        "- Rerun agent-bridge gate before claiming acceptance.",
    ])
    return f"""<!-- agent-bridge:closeout:start {task_id} -->
### {task_id}

Status: {status}

Gate checks:

```yaml
{yaml.safe_dump(gate.get('checks', {}), sort_keys=True).strip()}
```

Reasons:

{reason_lines}

Changed files:

{changed_file_lines}

Git facts:

{source_lines}

Evidence summary:

{evidence_summary}

GitHub evidence:

{github_summary}

GitHub Issue evidence:

{issue_summary}

Known risks:

{risk_lines}

Followups:

{followup_lines}

Resume:

{resume_lines}
<!-- agent-bridge:closeout:end {task_id} -->
"""


def upsert_block(text: str, task_id: str, block: str) -> str:
    pattern = re.compile(rf"<!-- agent-bridge:closeout:start {re.escape(task_id)} -->.*?<!-- agent-bridge:closeout:end {re.escape(task_id)} -->\n?", re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block, text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block


def command_closeout(args: argparse.Namespace) -> int:
    milestone = resolve_milestone(args.milestone, args.task)
    tasks, errors = load_validated_tasks(milestone)
    if errors:
        return emit({"result": GATE_INCONCLUSIVE, "reasons": errors}, args.json)
    selected = tasks
    if args.task:
        selected = [task for task in tasks if task.get("task_id") == args.task]
        if not selected:
            return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": [{"code": "task_not_found", "message": f"{args.task} not found."}]}, args.json)
    path = CLOSEOUT_ROOT / f"{args.milestone_name}.md"
    text = path.read_text(encoding="utf-8") if path.exists() else f"# {args.milestone_name} Closeout\n"
    results = []
    for task in selected:
        gate = gate_payload(task)
        text = upsert_block(text, task["task_id"], closeout_block(task, gate, milestone))
        results.append({"task_id": task["task_id"], "result": gate["result"]})
    if not args.dry_run:
        CLOSEOUT_ROOT.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    result_values = {item["result"] for item in results}
    if GATE_FAILED in result_values:
        aggregate_result = GATE_FAILED
    elif GATE_INCONCLUSIVE in result_values:
        aggregate_result = GATE_INCONCLUSIVE
    else:
        aggregate_result = "pass"
    payload = {"result": aggregate_result, "closeout": rel(path), "dry_run": args.dry_run, "tasks": results, "reasons": []}
    return emit(payload, args.json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("milestone")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=command_validate)

    task_info = sub.add_parser("task-info")
    task_info.add_argument("--task", required=True)
    task_info.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    task_info.add_argument("--json", action="store_true")
    task_info.set_defaults(func=command_task_info)

    diff = sub.add_parser("diff-check")
    diff.add_argument("--task", required=True)
    diff.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    diff.add_argument("--base")
    diff.add_argument("--head")
    diff.add_argument("--worktree", action="store_true")
    diff.add_argument("--include-path", action="append")
    diff.add_argument("--write-evidence", action="store_true")
    diff.add_argument("--json", action="store_true")
    diff.set_defaults(func=command_diff_check)

    evidence_init = sub.add_parser("evidence-init")
    evidence_init.add_argument("--task", required=True)
    evidence_init.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    evidence_init.add_argument("--dry-run", action="store_true")
    evidence_init.add_argument("--force", action="store_true")
    evidence_init.add_argument("--json", action="store_true")
    evidence_init.set_defaults(func=command_evidence_init)

    prompt_pack = sub.add_parser("prompt-pack")
    prompt_pack.add_argument("--task", required=True)
    prompt_pack.add_argument("--role", required=True, choices=sorted(PROMPT_ROLES))
    prompt_pack.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    prompt_pack.add_argument("--json", action="store_true")
    prompt_pack.set_defaults(func=command_prompt_pack)

    github_evidence = sub.add_parser("github-evidence")
    github_evidence.add_argument("--task", required=True)
    github_evidence.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    github_evidence.add_argument("--repo")
    github_evidence.add_argument("--pr")
    github_evidence.add_argument("--from-json")
    github_evidence.add_argument("--write-evidence", action="store_true")
    github_evidence.add_argument("--dry-run", action="store_true")
    github_evidence.add_argument("--json", action="store_true")
    github_evidence.set_defaults(func=command_github_evidence)

    issue_plan = sub.add_parser("issue-plan")
    issue_plan.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    issue_plan.add_argument("--repo")
    issue_plan.add_argument("--json", action="store_true")
    issue_plan.set_defaults(func=command_issue_plan)

    issue_export = sub.add_parser("issue-export")
    issue_export.add_argument("--task", required=True)
    issue_export.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    issue_export.add_argument("--repo")
    issue_export.add_argument("--issue")
    issue_export.add_argument("--write", action="store_true")
    issue_export.add_argument("--json", action="store_true")
    issue_export.set_defaults(func=command_issue_export)

    issue_status = sub.add_parser("issue-status")
    issue_status.add_argument("--task", required=True)
    issue_status.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    issue_status.add_argument("--repo")
    issue_status.add_argument("--issue")
    issue_status.add_argument("--from-json")
    issue_status.add_argument("--write-evidence", action="store_true")
    issue_status.add_argument("--json", action="store_true")
    issue_status.set_defaults(func=command_issue_status)

    issue_comment = sub.add_parser("issue-comment")
    issue_comment.add_argument("--task", required=True)
    issue_comment.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    issue_comment.add_argument("--repo")
    issue_comment.add_argument("--issue")
    issue_comment.add_argument("--write", action="store_true")
    issue_comment.add_argument("--write-evidence", action="store_true")
    issue_comment.add_argument("--json", action="store_true")
    issue_comment.set_defaults(func=command_issue_comment)

    gate = sub.add_parser("gate")
    gate.add_argument("--task", required=True)
    gate.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    gate.add_argument("--write-report", action="store_true")
    gate.add_argument("--json", action="store_true")
    gate.set_defaults(func=command_gate)

    closeout = sub.add_parser("closeout")
    closeout.add_argument("--task")
    closeout.add_argument("--milestone", default=str(DEFAULT_MILESTONE))
    closeout.add_argument("--milestone-name", default="M1")
    closeout.add_argument("--dry-run", action="store_true")
    closeout.add_argument("--json", action="store_true")
    closeout.set_defaults(func=command_closeout)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
