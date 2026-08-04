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


def write_ledger(cwd, tasks, root=None):
    ledger_path = cwd / ".codex" / "subagent-orchestration" / "ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps({"root": str(cwd if root is None else root), "tasks": tasks}),
        encoding="utf-8",
    )


def write_evidence(cwd, *names):
    evidence = cwd / "evidence"
    evidence.mkdir(exist_ok=True)
    for name in names:
        (evidence / name).write_text("proof", encoding="utf-8")


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
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def assert_block(self, result, fragment):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "block")
        self.assertIn(fragment, payload["reason"])

    def assert_deny(self, result, fragment):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        payload = json.loads(result.stdout)
        output = payload["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn(fragment, output["permissionDecisionReason"])

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

    def test_pretooluse_ignores_malformed_ledger_for_unrelated_and_unmarked_calls(self):
        ledger_path = self.cwd / ".codex" / "subagent-orchestration" / "ledger.json"
        ledger_path.parent.mkdir(parents=True)
        ledger_path.write_text("{not-json}", encoding="utf-8")
        unrelated = run_hook(
            self.cwd,
            "PreToolUse",
            {"tool_name": "read_file", "tool_input": {"path": "README.md"}},
        )
        unmarked = run_hook(
            self.cwd,
            "PreToolUse",
            {"tool_name": "spawn_agent", "tool_input": {"prompt": "Do the task."}},
        )
        self.assert_no_output(unrelated)
        self.assert_no_output(unmarked)

    def test_invalid_utf8_ledger_fails_closed_only_for_orchestrated_hooks(self):
        ledger_path = self.cwd / ".codex" / "subagent-orchestration" / "ledger.json"
        ledger_path.parent.mkdir(parents=True)
        ledger_path.write_bytes(b"\xff\xfe")
        unrelated = run_hook(
            self.cwd,
            "PreToolUse",
            {"tool_name": "read_file", "tool_input": {"path": "README.md"}},
        )
        unmarked = run_hook(
            self.cwd,
            "PreToolUse",
            {"tool_name": "spawn_agent", "tool_input": {"prompt": "Do the task."}},
        )
        marked = run_hook(
            self.cwd,
            "PreToolUse",
            {
                "tool_name": "spawn_agent",
                "tool_input": {"prompt": "ORCHESTRATION_TASK_ID: task-1"},
            },
        )
        stopped = run_hook(self.cwd, "Stop", {})
        subagent_stopped = run_hook(
            self.cwd,
            "SubagentStop",
            {"agent_id": "agent-1", "last_assistant_message": "done"},
        )
        self.assert_no_output(unrelated)
        self.assert_no_output(unmarked)
        self.assert_deny(marked, "malformed or unreadable")
        self.assert_block(stopped, "malformed or unreadable")
        self.assert_block(subagent_stopped, "malformed or unreadable")

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
        self.assert_deny(result, "superpowers:test-driven-development")

    def test_pretooluse_denies_target_task_missing_required_schema_field(self):
        payload = {
            "tool_name": "spawn_agent",
            "tool_input": {
                "prompt": "ORCHESTRATION_TASK_ID: task-1",
                "items": [
                    {"type": "skill", "name": "superpowers:test-driven-development"}
                ],
            },
        }
        for field in (
            "agent_id",
            "status",
            "dependencies",
            "skills_required",
            "tools_required",
        ):
            with self.subTest(field=field):
                task = active_task()
                task.pop(field)
                write_ledger(self.cwd, {"task-1": task})
                self.assert_deny(run_hook(self.cwd, "PreToolUse", payload), field)

    def test_subagentstop_allows_unrelated_agent_and_valid_report(self):
        write_ledger(self.cwd, {"task-1": active_task()})
        write_evidence(self.cwd, "result.txt")
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

    def test_subagentstop_uses_report_task_id_for_reused_agent(self):
        first_task = active_task()
        first_task["skills_required"] = ["superpowers:writing-skills"]
        second_task = active_task()
        write_ledger(self.cwd, {"task-1": first_task, "task-2": second_task})
        write_evidence(self.cwd, "result.txt")
        result = run_hook(
            self.cwd,
            "SubagentStop",
            {
                "agent_id": "agent-1",
                "last_assistant_message": report(task_id="task-2"),
            },
        )
        self.assert_no_output(result)

    def test_subagentstop_blocks_invalid_status_and_ready_evidence_failures(self):
        write_ledger(self.cwd, {"task-1": active_task()})
        cases = {
            "invalid status": report(status="WAITING"),
            "missing evidence paths": report(evidence_paths={}),
            "path escape": report(evidence_paths={"files": ["../outside.txt"]}),
        }
        for name, message in cases.items():
            with self.subTest(name=name):
                result = run_hook(
                    self.cwd,
                    "SubagentStop",
                    {"agent_id": "agent-1", "last_assistant_message": message},
                )
                self.assert_block(result, name)

    def test_subagentstop_allows_blocked_required_tool_unavailable_with_actual_proof(self):
        write_ledger(self.cwd, {"task-1": active_task()})
        result = run_hook(
            self.cwd,
            "SubagentStop",
            {
                "agent_id": "agent-1",
                "last_assistant_message": "BLOCKED_REQUIRED_TOOL_UNAVAILABLE\n"
                + report(
                    status="BLOCKED",
                    skills_loaded=[],
                    tools_proven=[],
                    evidence_paths={},
                ),
            },
        )
        self.assert_no_output(result)

    def test_subagentstop_requires_ready_coverage_and_valid_proof_arrays(self):
        write_ledger(self.cwd, {"task-1": active_task()})
        cases = {
            "skills_loaded": report(skills_loaded=[]),
            "tools_proven": report(tools_proven=[]),
            "invalid tools_proven": report(
                status="BLOCKED", tools_proven="playwright", evidence_paths={}
            ),
        }
        for reason, message in cases.items():
            with self.subTest(reason=reason):
                result = run_hook(
                    self.cwd,
                    "SubagentStop",
                    {"agent_id": "agent-1", "last_assistant_message": message},
                )
                self.assert_block(result, reason)

    def test_subagentstop_blocks_exact_task_missing_required_schema_field(self):
        write_evidence(self.cwd, "result.txt")
        for field in (
            "agent_id",
            "status",
            "dependencies",
            "skills_required",
            "tools_required",
        ):
            with self.subTest(field=field):
                task = active_task()
                task.pop(field)
                write_ledger(self.cwd, {"task-1": task})
                result = run_hook(
                    self.cwd,
                    "SubagentStop",
                    {"agent_id": "agent-1", "last_assistant_message": report()},
                )
                self.assert_block(result, field)

    def test_subagentstop_blocks_ledger_root_outside_hook_cwd(self):
        external_evidence = str(SCRIPT.resolve().relative_to("/"))
        write_ledger(self.cwd, {"task-1": active_task()}, root="/")
        result = run_hook(
            self.cwd,
            "SubagentStop",
            {
                "agent_id": "agent-1",
                "last_assistant_message": report(
                    evidence_paths={"files": [external_evidence]}
                ),
            },
        )
        self.assert_block(result, "current hook cwd")

    def test_subagentstop_blocks_unresolvable_evidence_path_without_traceback(self):
        loop = self.cwd / "evidence-loop"
        loop.symlink_to("evidence-loop")
        write_ledger(self.cwd, {"task-1": active_task()})
        result = run_hook(
            self.cwd,
            "SubagentStop",
            {
                "agent_id": "agent-1",
                "last_assistant_message": report(
                    evidence_paths={"files": ["evidence-loop/proof.txt"]}
                ),
            },
        )
        self.assert_block(result, "could not be validated")

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
        write_evidence(self.cwd, "result.txt", "command.log", "screen.png")
        write_ledger(self.cwd, {"task-1": accepted_task()})
        self.assert_no_output(run_hook(self.cwd, "Stop", {}))

    def test_explicit_empty_required_arrays_are_valid_for_all_hooks(self):
        task = active_task()
        task.update({"dependencies": [], "skills_required": [], "tools_required": []})
        write_ledger(self.cwd, {"task-1": task})
        pretool = run_hook(
            self.cwd,
            "PreToolUse",
            {
                "tool_name": "spawn_agent",
                "tool_input": {
                    "prompt": "ORCHESTRATION_TASK_ID: task-1",
                    "items": [],
                },
            },
        )
        subagent = run_hook(
            self.cwd,
            "SubagentStop",
            {
                "agent_id": "agent-1",
                "last_assistant_message": report(
                    status="BLOCKED",
                    skills_loaded=[],
                    tools_proven=[],
                    evidence_paths={},
                ),
            },
        )
        write_evidence(self.cwd, "result.txt")
        accepted = accepted_task(
            dependencies=[],
            skills_required=[],
            tools_required=[],
            skills_loaded=[],
            tools_proven=[],
            evidence_paths={"files": ["evidence/result.txt"]},
        )
        write_ledger(self.cwd, {"task-1": accepted})
        stopped = run_hook(self.cwd, "Stop", {})
        self.assert_no_output(pretool)
        self.assert_no_output(subagent)
        self.assert_no_output(stopped)

    def test_stop_allows_ledger_root_alias_resolving_to_hook_cwd(self):
        write_evidence(self.cwd, "result.txt", "command.log", "screen.png")
        root_alias = self.cwd / "workspace-alias"
        root_alias.symlink_to(self.cwd, target_is_directory=True)
        write_ledger(self.cwd, {"task-1": accepted_task()}, root=root_alias)
        self.assert_no_output(run_hook(self.cwd, "Stop", {}))

    def test_stop_blocks_ledger_root_outside_hook_cwd(self):
        external_evidence = str(SCRIPT.resolve().relative_to("/"))
        task = accepted_task(evidence_paths={"files": [external_evidence]})
        write_ledger(self.cwd, {"task-1": task}, root="/")
        self.assert_block(run_hook(self.cwd, "Stop", {}), "current hook cwd")

    def test_stop_blocks_empty_accepted_metadata(self):
        write_evidence(self.cwd, "result.txt", "command.log", "screen.png")
        for metadata in (
            {"by": "", "at": "2026-08-04T00:00:00Z"},
            {"by": "controller", "at": ""},
            {"by": "   ", "at": "2026-08-04T00:00:00Z"},
            {"by": "controller", "at": "\t\n"},
        ):
            with self.subTest(metadata=metadata):
                write_ledger(self.cwd, {"task-1": accepted_task(accepted=metadata)})
                self.assert_block(run_hook(self.cwd, "Stop", {}), "accepted metadata")

    def test_stop_blocks_task_missing_required_schema_field(self):
        write_evidence(self.cwd, "result.txt", "command.log", "screen.png")
        for field in (
            "agent_id",
            "status",
            "dependencies",
            "skills_required",
            "tools_required",
        ):
            with self.subTest(field=field):
                task = accepted_task()
                task.pop(field)
                write_ledger(self.cwd, {"task-1": task})
                self.assert_block(run_hook(self.cwd, "Stop", {}), field)

    def test_stop_blocks_invalid_evidence_path_without_traceback(self):
        task = accepted_task(evidence_paths={"files": ["bad\x00path"]})
        write_ledger(self.cwd, {"task-1": task})
        self.assert_block(
            run_hook(self.cwd, "Stop", {}),
            "could not be validated",
        )

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
