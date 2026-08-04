#!/usr/bin/env python3
"""Read-only Codex hook handler for the subagent orchestration ledger."""

import json
import sys
from pathlib import Path


LEDGER_RELATIVE_PATH = Path(".codex/subagent-orchestration/ledger.json")
REPORT_PREFIX = "ORCHESTRATION_REPORT:"


def emit(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")))


def block(reason):
    emit({"decision": "block", "reason": reason})


def deny_pretool(reason):
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def load_ledger(cwd):
    path = cwd / LEDGER_RELATIVE_PATH
    if not path.is_file():
        return None, None
    try:
        with path.open(encoding="utf-8") as handle:
            ledger = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None, "ledger JSON is malformed"
    if not isinstance(ledger, dict) or not isinstance(ledger.get("tasks"), dict):
        return None, "ledger must contain a tasks object"
    return ledger, None


def read_input():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings_in(child)


def tool_name(payload):
    for key in ("tool_name", "tool", "name"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def tool_input(payload):
    for key in ("tool_input", "tool_input_data", "arguments", "input"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return payload


def task_marker(value):
    marker = "ORCHESTRATION_TASK_ID:"
    for text in strings_in(value):
        if marker not in text:
            continue
        identifier = text.split(marker, 1)[1].strip().split()[0:1]
        if identifier:
            return identifier[0]
    return None


def supplied_skills(value):
    items = value.get("items") if isinstance(value, dict) else None
    if not isinstance(items, list):
        return set()
    return {
        item.get("name")
        for item in items
        if isinstance(item, dict)
        and item.get("type") == "skill"
        and isinstance(item.get("name"), str)
    }


def string_set(value):
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return None
    return set(value)


def required_values(task, field):
    value = task.get(field, [])
    return string_set(value)


def coverage_error(task, required_field, supplied_field, label):
    required = required_values(task, required_field)
    supplied = string_set(task.get(supplied_field))
    if required is None:
        return "invalid %s" % required_field
    if supplied is None:
        return "missing %s" % supplied_field
    missing = sorted(required - supplied)
    if missing:
        return "missing %s: %s" % (label, ", ".join(missing))
    return None


def handle_pretooluse(ledger, payload):
    name = tool_name(payload)
    if not (name == "spawn_agent" or name.endswith(".spawn_agent")):
        return
    call_input = tool_input(payload)
    identifier = task_marker(call_input)
    if identifier is None:
        return
    task = ledger["tasks"].get(identifier)
    if not isinstance(task, dict):
        deny_pretool("ORCHESTRATION_TASK_ID %s is not present in the ledger" % identifier)
        return
    required = required_values(task, "skills_required")
    if required is None:
        deny_pretool("task %s has invalid skills_required" % identifier)
        return
    missing = sorted(required - supplied_skills(call_input))
    if missing:
        deny_pretool(
            "task %s is missing structured skill items: %s" % (identifier, ", ".join(missing))
        )


def final_message(payload):
    for key in ("last_assistant_message", "last_message", "message", "output"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def report_error(task_id, task, message):
    if not isinstance(message, str) or not message:
        return "task %s requires a final %s JSON object" % (task_id, REPORT_PREFIX)
    line = message.splitlines()[-1]
    if not line.startswith(REPORT_PREFIX):
        return "task %s requires final line %s followed by one JSON object" % (task_id, REPORT_PREFIX)
    try:
        report = json.loads(line[len(REPORT_PREFIX) :].strip())
    except json.JSONDecodeError:
        return "task %s report must contain valid JSON" % task_id
    if not isinstance(report, dict):
        return "task %s report must be a JSON object" % task_id
    if report.get("task_id") != task_id:
        return "task %s report task_id does not match" % task_id
    if not isinstance(report.get("status"), str) or not report["status"]:
        return "task %s report is missing status" % task_id
    for required_field, label in (("skills_loaded", "skill proof"), ("tools_proven", "tool proof")):
        supplied = string_set(report.get(required_field))
        if supplied is None:
            return "task %s report is missing %s" % (task_id, required_field)
        requirements = required_values(task, "skills_required" if required_field == "skills_loaded" else "tools_required")
        if requirements is None:
            return "task %s has invalid ledger requirements" % task_id
        missing = sorted(requirements - supplied)
        if missing:
            return "task %s report is missing %s %s: %s" % (
                task_id,
                required_field,
                label,
                ", ".join(missing),
            )
    evidence_paths = report.get("evidence_paths")
    if not isinstance(evidence_paths, dict):
        return "task %s report is missing evidence_paths" % task_id
    return None


def handle_subagentstop(ledger, payload):
    agent_id = payload.get("agent_id")
    if not isinstance(agent_id, str):
        return
    matches = [
        (task_id, task)
        for task_id, task in ledger["tasks"].items()
        if isinstance(task, dict) and task.get("agent_id") == agent_id
    ]
    if not matches:
        return
    task_id, task = matches[0]
    error = report_error(task_id, task, final_message(payload))
    if error:
        block(error)


def ledger_root(ledger):
    root = ledger.get("root")
    if not isinstance(root, str) or not root:
        return None
    path = Path(root)
    if not path.is_absolute() or not path.is_dir():
        return None
    return path.resolve()


def evidence_error(task_id, evidence_paths, root):
    if not isinstance(evidence_paths, dict):
        return "task %s is missing evidence_paths" % task_id
    paths = []
    for evidence_type in ("files", "commands", "ui"):
        entries = evidence_paths.get(evidence_type, [])
        if not isinstance(entries, list) or not all(isinstance(item, str) and item for item in entries):
            return "task %s has invalid %s evidence paths" % (task_id, evidence_type)
        paths.extend((evidence_type, item) for item in entries)
    if not paths:
        return "task %s is missing evidence paths" % task_id
    for evidence_type, relative_path in paths:
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            return "task %s has path escape for %s evidence: %s" % (
                task_id,
                evidence_type,
                relative_path,
            )
        resolved = (root / candidate).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            return "task %s has path escape for %s evidence: %s" % (
                task_id,
                evidence_type,
                relative_path,
            )
        if not resolved.is_file():
            return "task %s has missing evidence: %s" % (task_id, relative_path)
        if resolved.stat().st_size == 0:
            return "task %s has empty evidence: %s" % (task_id, relative_path)
    return None


def handle_stop(ledger):
    root = ledger_root(ledger)
    if root is None:
        block("ledger root must be an existing absolute directory")
        return
    tasks = ledger["tasks"]
    for task_id, task in tasks.items():
        if not isinstance(task, dict) or task.get("status") != "accepted":
            continue
        dependencies = task.get("dependencies", [])
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            block("task %s has invalid dependencies" % task_id)
            return
        for dependency in dependencies:
            dependency_task = tasks.get(dependency)
            if not isinstance(dependency_task, dict) or dependency_task.get("status") != "accepted":
                block("task %s has unaccepted dependency: %s" % (task_id, dependency))
                return
        for required_field, supplied_field, label in (
            ("skills_required", "skills_loaded", "skill proof"),
            ("tools_required", "tools_proven", "tool proof"),
        ):
            error = coverage_error(task, required_field, supplied_field, label)
            if error:
                block("task %s has %s" % (task_id, error))
                return
        accepted = task.get("accepted")
        if not isinstance(accepted, dict) or not isinstance(accepted.get("by"), str) or not isinstance(accepted.get("at"), str):
            block("task %s is missing accepted metadata" % task_id)
            return
        error = evidence_error(task_id, task.get("evidence_paths"), root)
        if error:
            block(error)
            return


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"PreToolUse", "SubagentStop", "Stop"}:
        return 0
    ledger, ledger_error = load_ledger(Path.cwd())
    if ledger is None:
        if ledger_error:
            if sys.argv[1] == "PreToolUse":
                deny_pretool(ledger_error)
            else:
                block(ledger_error)
        return 0
    payload = read_input()
    if payload is None:
        if sys.argv[1] == "PreToolUse":
            deny_pretool("hook input must be valid JSON")
        else:
            block("hook input must be valid JSON")
        return 0
    if sys.argv[1] == "PreToolUse":
        handle_pretooluse(ledger, payload)
    elif sys.argv[1] == "SubagentStop":
        handle_subagentstop(ledger, payload)
    else:
        handle_stop(ledger)
    return 0


if __name__ == "__main__":
    sys.exit(main())
