import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "verify_ledger.py"


def run_hook(cwd, event, payload):
    return subprocess.run(
        [sys.executable, str(SCRIPT), event],
        cwd=cwd,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def write_ledger(cwd, tasks):
    ledger_path = cwd / ".codex" / "subagent-orchestration" / "ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps({"root": str(cwd), "tasks": tasks}), encoding="utf-8")


def active_task():
    return {
        "agent_id": "agent-1",
        "status": "active",
        "dependencies": [],
        "skills_required": ["superpowers:test-driven-development"],
        "tools_required": ["playwright"],
    }


def accepted_task(**overrides):
    task = active_task()
    task.update(
        {
            "status": "accepted",
            "skills_loaded": ["superpowers:test-driven-development"],
            "tools_proven": ["playwright"],
            "accepted": {"by": "controller", "at": "2026-08-04T00:00:00Z"},
            "evidence_paths": {
                "files": ["evidence/result.txt"],
                "commands": ["evidence/command.log"],
                "ui": ["evidence/screen.png"],
            },
        }
    )
    task.update(overrides)
    return task


def report(**overrides):
    payload = {
        "task_id": "task-1",
        "status": "READY_FOR_ACCEPTANCE",
        "skills_loaded": ["superpowers:test-driven-development"],
        "tools_proven": ["playwright"],
        "evidence_paths": {"files": ["evidence/result.txt"]},
    }
    payload.update(overrides)
    return "ORCHESTRATION_REPORT: " + json.dumps(payload)


class VerifyLedgerHooksTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def assert_no_output(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def assert_block(self, result, fragment):
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "block")
        self.assertIn(fragment, payload["reason"])

    def test_absent_ledger_is_noop_for_every_hook(self):
        for event, payload in (
            ("PreToolUse", {"tool_name": "spawn_agent", "tool_input": {"prompt": "x"}}),
            ("SubagentStop", {"agent_id": "agent-1", "last_assistant_message": "done"}),
            ("Stop", {}),
        ):
            with self.subTest(event=event):
                self.assert_no_output(run_hook(self.cwd, event, payload))

    def test_pretooluse_allows_unrelated_call_and_complete_structured_skills(self):
        write_ledger(self.cwd, {"task-1": active_task()})
        unrelated = run_hook(
            self.cwd,
            "PreToolUse",
            {"tool_name": "read_file", "tool_input": {"path": "README.md"}},
        )
        allowed = run_hook(
            self.cwd,
            "PreToolUse",
            {
                "tool_name": "spawn_agent",
                "tool_input": {
                    "prompt": "ORCHESTRATION_TASK_ID: task-1\nDo the task.",
                    "items": [{"type": "skill", "name": "superpowers:test-driven-development"}],
                },
            },
        )
        self.assert_no_output(unrelated)
        self.assert_no_output(allowed)

    def test_pretooluse_denies_missing_structured_skill_item(self):
        write_ledger(self.cwd, {"task-1": active_task()})
        result = run_hook(
            self.cwd,
            "PreToolUse",
            {
                "tool_name": "spawn_agent",
                "tool_input": {
                    "prompt": "ORCHESTRATION_TASK_ID: task-1",
                    "items": [{"type": "text", "text": "superpowers:test-driven-development"}],
                },
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        output = payload["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("superpowers:test-driven-development", output["permissionDecisionReason"])

    def test_subagentstop_allows_unrelated_agent_and_valid_report(self):
        write_ledger(self.cwd, {"task-1": active_task()})
        unrelated = run_hook(
            self.cwd,
            "SubagentStop",
            {"agent_id": "other-agent", "last_assistant_message": "done"},
        )
        valid = run_hook(
            self.cwd,
            "SubagentStop",
            {"agent_id": "agent-1", "last_assistant_message": report()},
        )
        self.assert_no_output(unrelated)
        self.assert_no_output(valid)

    def test_subagentstop_blocks_malformed_json_and_missing_skill_proof(self):
        write_ledger(self.cwd, {"task-1": active_task()})
        malformed = run_hook(
            self.cwd,
            "SubagentStop",
            {
                "agent_id": "agent-1",
                "last_assistant_message": "ORCHESTRATION_REPORT: {not-json}",
            },
        )
        missing_skill = run_hook(
            self.cwd,
            "SubagentStop",
            {
                "agent_id": "agent-1",
                "last_assistant_message": report(skills_loaded=[]),
            },
        )
        self.assert_block(malformed, "valid JSON")
        self.assert_block(missing_skill, "skills_loaded")

    def test_stop_allows_valid_accepted_ledger(self):
        evidence = self.cwd / "evidence"
        evidence.mkdir()
        for name in ("result.txt", "command.log", "screen.png"):
            (evidence / name).write_text("proof", encoding="utf-8")
        write_ledger(self.cwd, {"task-1": accepted_task()})
        self.assert_no_output(run_hook(self.cwd, "Stop", {}))

    def test_stop_blocks_path_escape_empty_evidence_and_missing_skill_proof(self):
        evidence = self.cwd / "evidence"
        evidence.mkdir()
        (evidence / "result.txt").write_text("proof", encoding="utf-8")
        (evidence / "command.log").write_text("proof", encoding="utf-8")
        (evidence / "screen.png").write_text("", encoding="utf-8")

        cases = {
            "path escape": accepted_task(evidence_paths={"files": ["../outside.txt"]}),
            "empty evidence": accepted_task(),
            "missing skill proof": accepted_task(skills_loaded=[]),
        }
        for name, task in cases.items():
            with self.subTest(name=name):
                write_ledger(self.cwd, {"task-1": task})
                self.assert_block(run_hook(self.cwd, "Stop", {}), name)


if __name__ == "__main__":
    unittest.main()
