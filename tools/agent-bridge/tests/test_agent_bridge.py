from __future__ import annotations

import contextlib
import io
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


MODULE_PATH = Path(__file__).resolve().parents[1] / "agent_bridge.py"
spec = importlib.util.spec_from_file_location("agent_bridge", MODULE_PATH)
agent_bridge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(agent_bridge)


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def task(**overrides):
    data = {
        "schema_version": 1,
        "task_id": "FX-T01",
        "title": "Task",
        "canonical_owner": "repo-doc",
        "revision": 1,
        "mode": "direct",
        "risk": "low",
        "lifecycle_status": "ready",
        "allowed_paths": ["docs/**"],
        "forbidden_paths": [".env", ".env.*", "secrets/**", "infra/prod/**"],
        "managed_artifact_paths": ["docs/milestones/evidence/FX-T01/**"],
        "acceptance": ["Pass."],
        "required_evidence": {
            "verifier": "not_applicable",
            "reviewer": "not_applicable",
            "functional_test": "not_applicable",
        },
        "backend_refs": {},
        "stop_conditions": [],
    }
    data.update(overrides)
    return data


def write_path_policy(evidence_dir: Path):
    (evidence_dir / "path-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "task_id": "FX-T01",
                "result": "pass",
                "source": {"mode": "worktree"},
                "changed_files": ["docs/readme.md"],
                "reasons": [],
            }
        ),
        encoding="utf-8",
    )


def write_github_pr(evidence_dir: Path, head_sha: str = "head-sha"):
    (evidence_dir / "github-pr.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "task_id": "FX-T01",
                "source": "github",
                "collection": {"mode": "fixture", "network": False, "source": "from-json"},
                "github_pr": {
                    "repo": "Notyet1307/Coshare",
                    "pr_number": 1,
                    "pr_url": "https://github.com/Notyet1307/Coshare/pull/1",
                    "state": "open",
                    "draft": False,
                    "base_branch": "main",
                    "head_branch": "phase-3-fixture",
                    "base_sha": "base-sha",
                    "head_sha": head_sha,
                    "mergeable_state": "clean",
                    "queried_at": "2026-06-12T00:00:00Z",
                    "conclusion": "pass",
                },
            }
        ),
        encoding="utf-8",
    )


def write_github_ci(evidence_dir: Path, conclusion: str = "pass", head_sha: str = "head-sha"):
    check_conclusion = "failure" if conclusion in {"fail", "failed", "failure"} else "success"
    (evidence_dir / "github-ci.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "task_id": "FX-T01",
                "source": "github",
                "collection": {"mode": "fixture", "network": False, "source": "from-json"},
                "github_ci": {
                    "repo": "Notyet1307/Coshare",
                    "head_sha": head_sha,
                    "required_checks_known": True,
                    "workflow_runs": [{"name": "tests", "status": "completed", "conclusion": check_conclusion}],
                    "check_runs": [{"name": "tests", "status": "completed", "conclusion": check_conclusion}],
                    "status_checks": [],
                    "conclusion": conclusion,
                },
            }
        ),
        encoding="utf-8",
    )


class AgentBridgeTests(unittest.TestCase):
    def setUp(self):
        self.old_changed_paths = agent_bridge.changed_paths
        agent_bridge.changed_paths = lambda base, head, worktree: ["docs/readme.md"]

    def tearDown(self):
        agent_bridge.changed_paths = self.old_changed_paths

    def test_valid_milestone_parses(self):
        tasks, errors = agent_bridge.load_validated_tasks(FIXTURES / "valid_milestone.md")
        self.assertEqual(errors, [])
        self.assertEqual([item["task_id"] for item in tasks], ["FX-T01"])

    def test_missing_fields_fail_validation(self):
        _, errors = agent_bridge.load_validated_tasks(FIXTURES / "invalid_missing.md")
        codes = {error["code"] for error in errors}
        self.assertIn("missing_required_field", codes)
        self.assertIn("empty_acceptance", codes)

    def test_duplicate_task_ids_fail_validation(self):
        _, errors = agent_bridge.load_validated_tasks(FIXTURES / "invalid_duplicate.md")
        self.assertIn("duplicate_task_id", {error["code"] for error in errors})

    def test_forbidden_path_change_fails_diff_check(self):
        payload = agent_bridge.diff_check_payload(task(), [".env", "docs/readme.md"])
        self.assertEqual(payload["result"], "fail")
        self.assertEqual(payload["reasons"][0]["code"], "forbidden_path_changed")

    def test_allowed_path_change_passes_diff_check(self):
        payload = agent_bridge.diff_check_payload(task(), ["docs/readme.md"])
        self.assertEqual(payload["result"], "pass")
        self.assertEqual(payload["reasons"], [])

    def test_rename_and_delete_paths_are_parsed(self):
        output = "R100\told.md\tdocs/new.md\nD\tdocs/deleted.md\n"
        self.assertEqual(agent_bridge.parse_name_status(output), ["docs/deleted.md", "docs/new.md", "old.md"])

    def test_verifier_command_failure_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "verifier.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "verifier": {
                            "commands": [{"command": "false", "exit_code": 1}],
                            "conclusion": "fail",
                        },
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "required", "reviewer": "not_applicable", "functional_test": "not_applicable"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "failed")
        self.assertEqual(payload["reasons"][0]["code"], "verifier_command_failed")

    def test_open_reviewer_p1_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "reviewer.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "reviewer": {
                            "findings": [
                                {
                                    "severity": "P1",
                                    "status": "open",
                                    "file": "docs/x.md",
                                    "issue": "Blocking issue",
                                    "required_action": "Fix it",
                                }
                            ],
                            "conclusion": "fail",
                        },
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "not_applicable", "reviewer": "required", "functional_test": "not_applicable"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "failed")
        self.assertEqual(payload["reasons"][0]["code"], "open_blocking_reviewer_finding")

    def test_reviewer_p1_without_status_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "reviewer.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "reviewer": {
                            "findings": [{"severity": "P1", "file": "docs/x.md", "issue": "Missing status"}],
                            "conclusion": "pass",
                        },
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "not_applicable", "reviewer": "required", "functional_test": "not_applicable"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "missing_reviewer_finding_status")

    def test_missing_required_evidence_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "required", "reviewer": "not_applicable", "functional_test": "not_applicable"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")

    def test_missing_path_policy_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "missing_path_policy")

    def test_empty_path_policy_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            (evidence_dir / "path-policy.yaml").write_text(
                yaml.safe_dump({"schema_version": 1, "task_id": "FX-T01", "source": {"mode": "worktree"}}),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "invalid_path_policy_result")

    def test_path_policy_without_source_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            (evidence_dir / "path-policy.yaml").write_text(
                yaml.safe_dump({"schema_version": 1, "task_id": "FX-T01", "result": "pass", "changed_files": [], "reasons": []}),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "missing_path_policy_source")

    def test_path_policy_task_id_mismatch_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            (evidence_dir / "path-policy.yaml").write_text(
                yaml.safe_dump({"schema_version": 1, "task_id": "WRONG-TASK", "result": "pass", "source": {"mode": "worktree"}, "changed_files": [], "reasons": []}),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "evidence_task_id_mismatch")

    def test_verifier_task_id_mismatch_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "verifier.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "WRONG-TASK",
                        "verifier": {"commands": [{"command": "true", "exit_code": 0}], "conclusion": "pass"},
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "required", "reviewer": "not_applicable", "functional_test": "not_applicable"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "evidence_task_id_mismatch")

    def test_reviewer_schema_version_mismatch_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "reviewer.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 2,
                        "task_id": "FX-T01",
                        "reviewer": {"findings": [], "conclusion": "pass"},
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "not_applicable", "reviewer": "required", "functional_test": "not_applicable"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "invalid_evidence_schema_version")

    def test_path_policy_pass_with_forbidden_reason_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            (evidence_dir / "path-policy.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "result": "pass",
                        "source": {"mode": "worktree"},
                        "changed_files": [],
                        "reasons": [{"code": "forbidden_path_changed", "path": ".env", "message": "Changed file is under forbidden_paths."}],
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "failed")
        self.assertEqual(payload["reasons"][0]["code"], "forbidden_path_changed")

    def test_path_policy_pass_with_forbidden_changed_file_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            (evidence_dir / "path-policy.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "result": "pass",
                        "source": {"mode": "worktree"},
                        "changed_files": [".env"],
                        "reasons": [],
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "failed")
        self.assertEqual(payload["reasons"][0]["code"], "forbidden_path_changed")

    def test_path_policy_changed_files_must_match_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            old_changed_paths = agent_bridge.changed_paths
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            agent_bridge.changed_paths = lambda base, head, worktree: ["docs/actual.md"]
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            (evidence_dir / "path-policy.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "result": "pass",
                        "source": {"mode": "worktree"},
                        "changed_files": ["docs/claimed.md"],
                        "reasons": [],
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
                agent_bridge.changed_paths = old_changed_paths
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "path_policy_changed_files_mismatch")

    def test_empty_reviewer_evidence_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "reviewer.yaml").write_text(
                yaml.safe_dump({"schema_version": 1, "task_id": "FX-T01"}),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "not_applicable", "reviewer": "required", "functional_test": "not_applicable"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "missing_reviewer_block")

    def test_invalid_reviewer_finding_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "reviewer.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "reviewer": {"findings": ["not-a-mapping"], "conclusion": "pass"},
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "not_applicable", "reviewer": "required", "functional_test": "not_applicable"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "invalid_reviewer_finding")

    def test_invalid_functional_test_level_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "functional-test.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "functional_test": {"level": "FT-L9", "conclusion": "pass"},
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task(required_evidence={"verifier": "not_applicable", "reviewer": "not_applicable", "functional_test": "required"}))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "invalid_functional_test_level")

    def test_invalid_blocker_schema_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            (evidence_dir / "blockers.yaml").write_text(
                yaml.safe_dump({"schema_version": 1, "task_id": "FX-T01", "blockers": [{"severity": "P2"}]}),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "invalid_blocker_schema")

    def test_closeout_block_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            try:
                gate = {"result": "accepted", "checks": {"verifier": "pass"}, "reasons": []}
                block = agent_bridge.closeout_block(task(), gate)
                first = agent_bridge.upsert_block("# Closeout\n", "FX-T01", block)
                second = agent_bridge.upsert_block(first, "FX-T01", block)
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(first, second)
        self.assertIn("Changed files:", block)
        self.assertIn("Git facts:", block)
        self.assertIn("Evidence summary:", block)
        self.assertIn("Known risks:", block)
        self.assertIn("Followups:", block)
        self.assertIn("Resume:", block)

    def test_closeout_dry_run_does_not_write_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_closeout = agent_bridge.CLOSEOUT_ROOT
            closeout_root = Path(tmp) / "closeout"
            agent_bridge.CLOSEOUT_ROOT = closeout_root
            args = type(
                "Args",
                (),
                {
                    "milestone": str(FIXTURES / "valid_milestone.md"),
                    "milestone_name": "FX",
                    "task": None,
                    "dry_run": True,
                    "json": True,
                },
            )()
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    exit_code = agent_bridge.command_closeout(args)
            finally:
                agent_bridge.CLOSEOUT_ROOT = old_closeout
        self.assertEqual(exit_code, 2)
        self.assertFalse((closeout_root / "FX.md").exists())
        self.assertFalse(closeout_root.exists())

    def test_closeout_dry_run_returns_inconclusive_when_selected_task_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_closeout = agent_bridge.CLOSEOUT_ROOT
            old_evidence = agent_bridge.EVIDENCE_ROOT
            agent_bridge.CLOSEOUT_ROOT = Path(tmp) / "closeout"
            agent_bridge.EVIDENCE_ROOT = Path(tmp) / "evidence"
            args = type(
                "Args",
                (),
                {
                    "milestone": str(FIXTURES / "valid_milestone.md"),
                    "milestone_name": "FX",
                    "task": None,
                    "dry_run": True,
                    "json": True,
                },
            )()
            try:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_code = agent_bridge.command_closeout(args)
                payload = yaml.safe_load(output.getvalue())
            finally:
                agent_bridge.CLOSEOUT_ROOT = old_closeout
                agent_bridge.EVIDENCE_ROOT = old_evidence
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["tasks"][0]["result"], "inconclusive")

    def test_task_info_payload_includes_contract_boundaries(self):
        item = task()
        payload = agent_bridge.task_info_payload(item, FIXTURES / "valid_milestone.md")
        self.assertEqual(payload["result"], "pass")
        self.assertEqual(payload["task"]["task_id"], "FX-T01")
        self.assertEqual(payload["task"]["allowed_paths"], ["docs/**"])
        self.assertIn(".env", payload["task"]["forbidden_paths"])

    def test_evidence_init_dry_run_does_not_write_and_is_not_false_pass_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            item = task(
                managed_artifact_paths=["**"],
                required_evidence={
                    "verifier": "required",
                    "reviewer": "required",
                    "functional_test": "not_applicable",
                }
            )
            try:
                payload = agent_bridge.evidence_init_payload(item, dry_run=True, force=False)
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "pass")
        self.assertEqual({entry["action"] for entry in payload["files"]}, {"would_create"})
        self.assertFalse((Path(tmp) / "FX-T01" / "verifier.yaml").exists())

    def test_evidence_init_writes_inconclusive_skeletons_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            item = task(
                managed_artifact_paths=["**"],
                required_evidence={
                    "verifier": "required",
                    "reviewer": "required",
                    "functional_test": "required",
                }
            )
            try:
                payload = agent_bridge.evidence_init_payload(item, dry_run=False, force=False)
                verifier = yaml.safe_load((Path(tmp) / "FX-T01" / "verifier.yaml").read_text(encoding="utf-8"))
                reviewer = yaml.safe_load((Path(tmp) / "FX-T01" / "reviewer.yaml").read_text(encoding="utf-8"))
                functional = yaml.safe_load((Path(tmp) / "FX-T01" / "functional-test.yaml").read_text(encoding="utf-8"))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "pass")
        self.assertEqual(verifier["verifier"]["conclusion"], "inconclusive")
        self.assertEqual(reviewer["reviewer"]["conclusion"], "inconclusive")
        self.assertEqual(functional["functional_test"]["conclusion"], "inconclusive")

    def test_prompt_pack_contains_role_boundaries(self):
        prompt = agent_bridge.prompt_for_role(task(), "builder", FIXTURES / "valid_milestone.md")
        self.assertIn("Milestone docs are the canonical task source.", prompt)
        self.assertIn("Allowed paths:", prompt)
        self.assertIn("Forbidden paths:", prompt)
        self.assertIn("Stop conditions:", prompt)
        self.assertIn("model API calls", prompt)

    def test_prompt_pack_reads_milestone_non_goals(self):
        prompt = agent_bridge.prompt_for_role(task(task_id="M2-T07"), "reviewer", agent_bridge.ROOT / "docs/milestones/M2.md")
        self.assertIn("GitHub Issue as canonical task source", prompt)
        self.assertIn("production secret handling", prompt)
        self.assertIn("VPN/internal network automation", prompt)

    def test_resolve_milestone_supports_task_prefix_and_shorthand(self):
        self.assertEqual(agent_bridge.resolve_milestone("M3"), (agent_bridge.ROOT / "docs/milestones/M3.md").resolve())
        self.assertEqual(agent_bridge.resolve_milestone(str(agent_bridge.DEFAULT_MILESTONE), "M3-T01"), (agent_bridge.ROOT / "docs/milestones/M3.md").resolve())

    def test_closeout_resume_uses_selected_milestone(self):
        gate = {"result": "accepted", "checks": {"verifier": "pass"}, "reasons": []}
        milestone = FIXTURES / "valid_milestone.md"
        block = agent_bridge.closeout_block(task(), gate, milestone)
        self.assertIn(f"Read {agent_bridge.rel(milestone)} for task FX-T01.", block)
        self.assertNotIn("docs/milestones/M2.md or the active milestone", block)

    def test_git_range_source_accepts_base_sha_head_sha(self):
        old_commit_exists = agent_bridge.git_commit_exists
        old_changed_paths = agent_bridge.changed_paths
        agent_bridge.git_commit_exists = lambda ref: ref in {"base", "head"}
        agent_bridge.changed_paths = lambda base, head, worktree: ["docs/readme.md"]
        try:
            paths, error = agent_bridge.changed_paths_from_source(
                {"mode": "git_range", "base_sha": "base", "head_sha": "head"}
            )
        finally:
            agent_bridge.git_commit_exists = old_commit_exists
            agent_bridge.changed_paths = old_changed_paths
        self.assertIsNone(error)
        self.assertEqual(paths, ["docs/readme.md"])

    def test_git_range_source_rejects_invalid_base_sha(self):
        old_commit_exists = agent_bridge.git_commit_exists
        agent_bridge.git_commit_exists = lambda ref: ref == "head"
        try:
            paths, error = agent_bridge.changed_paths_from_source(
                {"mode": "git_range", "base_sha": "missing", "head_sha": "head"}
            )
        finally:
            agent_bridge.git_commit_exists = old_commit_exists
        self.assertIsNone(paths)
        self.assertEqual(error["code"], "invalid_base_sha")

    def test_git_range_source_rejects_invalid_head_sha(self):
        old_commit_exists = agent_bridge.git_commit_exists
        agent_bridge.git_commit_exists = lambda ref: ref == "base"
        try:
            paths, error = agent_bridge.changed_paths_from_source(
                {"mode": "git_range", "base_sha": "base", "head_sha": "missing"}
            )
        finally:
            agent_bridge.git_commit_exists = old_commit_exists
        self.assertIsNone(paths)
        self.assertEqual(error["code"], "invalid_head_sha")

    def test_empty_git_range_with_base_sha_head_sha_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            old_commit_exists = agent_bridge.git_commit_exists
            old_changed_paths = agent_bridge.changed_paths
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            agent_bridge.git_commit_exists = lambda ref: ref == "same"
            agent_bridge.changed_paths = lambda base, head, worktree: []
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            (evidence_dir / "path-policy.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "result": "pass",
                        "source": {"mode": "git_range", "base_sha": "same", "head_sha": "same"},
                        "changed_files": [],
                        "reasons": [],
                    }
                ),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
                agent_bridge.git_commit_exists = old_commit_exists
                agent_bridge.changed_paths = old_changed_paths
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "empty_git_range_path_policy")

    def test_github_evidence_from_fixture_writes_pr_ci(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            args = type(
                "Args",
                (),
                {
                    "from_json": str(FIXTURES / "github" / "pass.json"),
                    "repo": None,
                    "pr": None,
                    "write_evidence": True,
                    "dry_run": False,
                },
            )()
            try:
                payload = agent_bridge.github_evidence_payload(task(), args)
                out_dir = Path(tmp) / "FX-T01"
                ci = yaml.safe_load((out_dir / "github-ci.yaml").read_text(encoding="utf-8"))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "pass")
        self.assertTrue(any(item["path"].endswith("github-pr.yaml") for item in payload["files"]))
        self.assertEqual(ci["github_ci"]["conclusion"], "pass")

    def test_github_fixture_normalization_redacts_token_like_values(self):
        evidence = agent_bridge.normalize_github_fixture(
            "FX-T01",
            {
                "token": "ghp_runtime_only_value",
                "github_pr": {
                    "repo": "Notyet1307/Coshare",
                    "pr_number": 1,
                    "pr_url": "https://github.com/Notyet1307/Coshare/pull/1",
                    "state": "open",
                    "draft": False,
                    "base_branch": "main",
                    "head_branch": "phase-3-fixture",
                    "base_sha": "base-sha",
                    "head_sha": "head-sha",
                    "queried_at": "2026-06-12T00:00:00Z",
                },
            },
        )
        text = yaml.safe_dump(evidence, sort_keys=False)
        self.assertNotIn("ghp_runtime_only_value", text)

    def test_github_check_bucket_values_are_normalized(self):
        self.assertEqual(agent_bridge.github_conclusion("pass"), "pass")
        self.assertEqual(agent_bridge.github_conclusion("fail"), "fail")
        self.assertEqual(agent_bridge.github_conclusion("cancel"), "fail")
        self.assertEqual(agent_bridge.github_conclusion("pending"), "inconclusive")
        self.assertEqual(agent_bridge.github_conclusion("skipping"), "skipped")

    def test_live_github_evidence_writes_inconclusive_ci_when_checks_unavailable(self):
        old_run_gh_json = agent_bridge.run_gh_json

        def fake_run_gh_json(args):
            if args[:2] == ["pr", "view"]:
                return {
                    "number": 1,
                    "url": "https://github.com/Notyet1307/Coshare/pull/1",
                    "state": "OPEN",
                    "isDraft": False,
                    "baseRefName": "main",
                    "headRefName": "branch",
                    "baseRefOid": "base-sha",
                    "headRefOid": "head-sha",
                    "mergeable": "MERGEABLE",
                    "reviews": [],
                }, None
            if args[:2] == ["pr", "checks"]:
                return None, {"code": "github_read_failed", "message": "no checks reported"}
            return None, {"code": "unexpected_call", "message": "unexpected"}

        agent_bridge.run_gh_json = fake_run_gh_json
        try:
            evidence, reasons = agent_bridge.load_live_github_evidence("FX-T01", "Notyet1307/Coshare", "1")
        finally:
            agent_bridge.run_gh_json = old_run_gh_json
        self.assertEqual(reasons, [])
        self.assertIn("github-ci.yaml", evidence)
        self.assertEqual(evidence["github-ci.yaml"]["github_ci"]["conclusion"], "inconclusive")
        self.assertEqual(evidence["github-ci.yaml"]["github_ci"]["reasons"][0]["code"], "github_read_failed")

    def test_github_evidence_missing_required_pr_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            try:
                payload = agent_bridge.gate_payload(task(required_github_evidence=["pr"]))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertIn("missing_github_pr_evidence", {reason["code"] for reason in payload["reasons"]})

    def test_github_ci_failure_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            write_github_ci(evidence_dir, conclusion="fail")
            try:
                payload = agent_bridge.gate_payload(task(required_github_evidence=["ci"]))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "failed")
        self.assertIn("github_ci_failed", {reason["code"] for reason in payload["reasons"]})

    def test_github_pr_head_sha_mismatch_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            old_commit_exists = agent_bridge.git_commit_exists
            old_changed_paths = agent_bridge.changed_paths
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            agent_bridge.git_commit_exists = lambda ref: ref in {"base-sha", "task-head-sha"}
            agent_bridge.changed_paths = lambda base, head, worktree: ["docs/readme.md"]
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            (evidence_dir / "path-policy.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "task_id": "FX-T01",
                        "result": "pass",
                        "source": {"mode": "git_range", "base_sha": "base-sha", "head_sha": "task-head-sha"},
                        "changed_files": ["docs/readme.md"],
                        "reasons": [],
                    }
                ),
                encoding="utf-8",
            )
            write_github_pr(evidence_dir, head_sha="github-head-sha")
            try:
                payload = agent_bridge.gate_payload(task(required_github_evidence=["pr"], github_sha_consistency_required=True))
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
                agent_bridge.git_commit_exists = old_commit_exists
                agent_bridge.changed_paths = old_changed_paths
        self.assertEqual(payload["result"], "failed")
        self.assertIn("github_pr_head_sha_mismatch", {reason["code"] for reason in payload["reasons"]})

    def test_closeout_block_includes_github_evidence_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_root = agent_bridge.EVIDENCE_ROOT
            agent_bridge.EVIDENCE_ROOT = Path(tmp)
            evidence_dir = Path(tmp) / "FX-T01"
            evidence_dir.mkdir()
            write_path_policy(evidence_dir)
            write_github_pr(evidence_dir)
            write_github_ci(evidence_dir)
            try:
                gate = agent_bridge.gate_payload(task(required_github_evidence=["pr", "ci"]))
                block = agent_bridge.closeout_block(task(required_github_evidence=["pr", "ci"]), gate, FIXTURES / "valid_milestone.md")
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertIn("GitHub evidence:", block)
        self.assertIn("https://github.com/Notyet1307/Coshare/pull/1", block)
        self.assertIn("CI conclusion: pass", block)


if __name__ == "__main__":
    unittest.main()
