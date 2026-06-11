from __future__ import annotations

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
                "changed_files": ["docs/readme.md"],
                "reasons": [],
            }
        ),
        encoding="utf-8",
    )


class AgentBridgeTests(unittest.TestCase):
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
                yaml.safe_dump({"schema_version": 1, "task_id": "FX-T01"}),
                encoding="utf-8",
            )
            try:
                payload = agent_bridge.gate_payload(task())
            finally:
                agent_bridge.EVIDENCE_ROOT = old_root
        self.assertEqual(payload["result"], "inconclusive")
        self.assertEqual(payload["reasons"][0]["code"], "invalid_path_policy_result")

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

    def test_closeout_block_is_idempotent(self):
        gate = {"result": "accepted", "checks": {"verifier": "pass"}, "reasons": []}
        block = agent_bridge.closeout_block("FX-T01", gate)
        first = agent_bridge.upsert_block("# Closeout\n", "FX-T01", block)
        second = agent_bridge.upsert_block(first, "FX-T01", block)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
