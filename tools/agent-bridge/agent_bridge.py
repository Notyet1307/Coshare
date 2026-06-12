#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
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
PROMPT_ROLES = {
    "orchestrator",
    "builder",
    "test-builder",
    "verifier",
    "reviewer",
    "functional-tester",
    "closeout",
}


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
    try:
        if mode == "worktree":
            return changed_paths(None, None, True), None
        if mode == "git_range":
            base = source.get("base_sha") or source.get("base")
            head = source.get("head_sha") or source.get("head")
            if not base or not head:
                return None, {"code": "invalid_path_policy_source", "message": "git_range source requires base_sha/head_sha or base/head."}
            if not git_commit_exists(str(base)):
                return None, {"code": "invalid_base_sha", "message": f"base_sha does not resolve: {base}"}
            if not git_commit_exists(str(head)):
                return None, {"code": "invalid_head_sha", "message": f"head_sha does not resolve: {head}"}
            return changed_paths(str(base), str(head), False), None
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
    if source.get("mode") == "git_range" and source.get("base") == source.get("head") and changed_files == []:
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


def gate_payload(task: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "path_policy": check_path_policy(task),
        "verifier": check_verifier(task),
        "reviewer": check_reviewer(task),
        "functional_test": check_functional(task),
        "blockers": check_blockers(task),
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
    path = Path(args.milestone).resolve()
    tasks, errors = load_validated_tasks(path)
    payload = {
        "result": "invalid" if errors else "valid",
        "milestone": rel(path) if path.is_relative_to(ROOT) else str(path),
        "tasks_checked": len(tasks),
        "reasons": errors,
    }
    return emit(payload, args.json)


def command_diff_check(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, Path(args.milestone).resolve())
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
    milestone = Path(args.milestone).resolve()
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
    task, errors = find_task(args.task, Path(args.milestone).resolve())
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
- Multica integration
- GitHub Issue sync
- GitLab integration
- dashboard
- auto-merge
- model API calls
- autonomous long-running loops
- worker metrics routing
- bidirectional sync
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
    milestone = Path(args.milestone).resolve()
    task, errors = find_task(args.task, milestone)
    if errors or task is None:
        return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": errors}, args.json)
    prompt = prompt_for_role(task, args.role, milestone)
    payload = {"result": "pass", "task_id": args.task, "role": args.role, "prompt": prompt, "reasons": []}
    if args.json:
        return emit(payload, True)
    print(prompt)
    return 0


def command_gate(args: argparse.Namespace) -> int:
    task, errors = find_task(args.task, Path(args.milestone).resolve())
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


def closeout_block(task: dict[str, Any], gate: dict[str, Any]) -> str:
    task_id = task["task_id"]
    status = gate["result"]
    reasons = gate.get("reasons", [])
    reason_lines = "\n".join(f"- {r.get('code')}: {r.get('message', '')}" for r in reasons) or "- none"
    evidence_lines, changed_files = summarize_evidence(task)
    changed_file_lines = "\n".join(f"- {path}" for path in changed_files) or "- none"
    evidence_summary = "\n".join(evidence_lines) or "- none"
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
    resume_lines = "\n".join([
        f"- Read docs/milestones/M2.md or the active milestone for task {task_id}.",
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
    milestone = Path(args.milestone).resolve()
    tasks, errors = load_validated_tasks(milestone)
    if errors:
        return emit({"result": GATE_INCONCLUSIVE, "reasons": errors}, args.json)
    selected = tasks
    if args.task:
        selected = [task for task in tasks if task.get("task_id") == args.task]
        if not selected:
            return emit({"result": GATE_INCONCLUSIVE, "task_id": args.task, "reasons": [{"code": "task_not_found", "message": f"{args.task} not found."}]}, args.json)
    CLOSEOUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = CLOSEOUT_ROOT / f"{args.milestone_name}.md"
    text = path.read_text(encoding="utf-8") if path.exists() else f"# {args.milestone_name} Closeout\n"
    results = []
    for task in selected:
        gate = gate_payload(task)
        text = upsert_block(text, task["task_id"], closeout_block(task, gate))
        results.append({"task_id": task["task_id"], "result": gate["result"]})
    if not args.dry_run:
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
