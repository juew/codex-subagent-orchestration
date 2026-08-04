#!/usr/bin/env python3
"""Read-only Codex hook handler for the subagent orchestration ledger."""

import json
import stat
import sys
from pathlib import Path


LEDGER_RELATIVE_PATH = Path(".codex/subagent-orchestration/ledger.json")
REPORT_PREFIX = "ORCHESTRATION_REPORT:"
LEDGER_ROOT_ERROR = (
    "ledger root must be an existing absolute directory resolving to the current hook cwd"
)
LEDGER_READ_ERROR = "ledger JSON is malformed or unreadable"
HOOK_CWD_ERROR = "hook cwd could not be resolved"
PATH_ERRORS = (OSError, ValueError, RuntimeError)
TASK_ARRAY_FIELDS = ("dependencies", "skills_required", "tools_required")
ALLOWED_REPORT_STATUSES = {
    "READY_FOR_ACCEPTANCE",
    "BLOCKED",
    "FAIL",
    "NEEDS_CLARIFICATION",
}


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
    try:
        path.lstat()
    except FileNotFoundError:
        return None, None
    except PATH_ERRORS:
        return None, LEDGER_READ_ERROR
    try:
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            return None, LEDGER_READ_ERROR
        with path.open(encoding="utf-8") as handle:
            ledger = json.load(handle)
    except (OSError, UnicodeError, ValueError, RuntimeError):
        return None, LEDGER_READ_ERROR
    if not isinstance(ledger, dict) or not isinstance(ledger.get("tasks"), dict):
        return None, "ledger must contain a tasks object"
    return ledger, None


def read_input():
    try:
        payload = json.load(sys.stdin)
    except (OSError, UnicodeError, ValueError, RuntimeError):
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


def is_marked_spawn(payload):
    if not isinstance(payload, dict):
        return False
    name = tool_name(payload)
    return (name == "spawn_agent" or name.endswith(".spawn_agent")) and task_marker(
        tool_input(payload)
    ) is not None


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


def task_shape_error(task):
    if not isinstance(task, dict):
        return "task must be an object"
    for field in ("agent_id", "status"):
        value = task.get(field)
        if not isinstance(value, str) or not value:
            return "missing or invalid %s" % field
    for field in TASK_ARRAY_FIELDS:
        if string_set(task.get(field)) is None:
            return "missing or invalid %s" % field
    return None


def required_values(task, field):
    return string_set(task.get(field))


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
    shape_error = task_shape_error(task)
    if shape_error:
        deny_pretool("task %s is invalid: %s" % (identifier, shape_error))
        return
    required = required_values(task, "skills_required")
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


def parse_report(message):
    if not isinstance(message, str) or not message:
        return None, "requires a final %s JSON object" % REPORT_PREFIX
    line = message.splitlines()[-1]
    if not line.startswith(REPORT_PREFIX):
        return None, "requires final line %s followed by one JSON object" % REPORT_PREFIX
    try:
        report = json.loads(line[len(REPORT_PREFIX) :].strip())
    except json.JSONDecodeError:
        return None, "report must contain valid JSON"
    if not isinstance(report, dict):
        return None, "report must be a JSON object"
    return report, None


def report_error(task_id, task, report, root):
    if report.get("task_id") != task_id:
        return "task %s report task_id does not match" % task_id
    status = report.get("status")
    if status not in ALLOWED_REPORT_STATUSES:
        return "task %s report has invalid status" % task_id
    proof_sets = {}
    for required_field in ("skills_loaded", "tools_proven"):
        supplied = string_set(report.get(required_field))
        if supplied is None:
            return "task %s report has invalid %s" % (task_id, required_field)
        proof_sets[required_field] = supplied
    if status == "READY_FOR_ACCEPTANCE":
        for required_field, supplied_field, label in (
            ("skills_required", "skills_loaded", "skill proof"),
            ("tools_required", "tools_proven", "tool proof"),
        ):
            missing = sorted(required_values(task, required_field) - proof_sets[supplied_field])
            if missing:
                return "task %s report is missing %s %s: %s" % (
                    task_id,
                    supplied_field,
                    label,
                    ", ".join(missing),
                )
    evidence_paths = report.get("evidence_paths")
    return evidence_error(
        task_id,
        evidence_paths,
        root,
        require_paths=status == "READY_FOR_ACCEPTANCE",
    )


def handle_subagentstop(ledger, payload, cwd):
    agent_id = payload.get("agent_id")
    if not isinstance(agent_id, str):
        return
    owns_task = any(
        isinstance(task, dict) and task.get("agent_id") == agent_id
        for task in ledger["tasks"].values()
    )
    message = final_message(payload)
    claims_report = (
        isinstance(message, str)
        and bool(message.splitlines())
        and message.splitlines()[-1].startswith(REPORT_PREFIX)
    )
    if not owns_task and not claims_report:
        return
    report, parse_error = parse_report(message)
    if parse_error:
        block("agent %s %s" % (agent_id, parse_error))
        return
    task_id = report.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        block("agent %s report has invalid task_id" % agent_id)
        return
    task = ledger["tasks"].get(task_id)
    if not isinstance(task, dict):
        block("task %s is not present in the ledger" % task_id)
        return
    shape_error = task_shape_error(task)
    if shape_error:
        block("task %s is invalid: %s" % (task_id, shape_error))
        return
    if task.get("agent_id") != agent_id:
        block("task %s is not assigned to agent %s" % (task_id, agent_id))
        return
    root = ledger_root(ledger, cwd)
    if root is None:
        block(LEDGER_ROOT_ERROR)
        return
    error = report_error(task_id, task, report, root)
    if error:
        block(error)


def ledger_root(ledger, cwd):
    root = ledger.get("root")
    if not isinstance(root, str) or not root:
        return None
    try:
        path = Path(root)
        if not path.is_absolute() or not path.is_dir():
            return None
        resolved = path.resolve()
        current = cwd.resolve()
    except PATH_ERRORS:
        return None
    if resolved != current:
        return None
    return resolved


def evidence_error(task_id, evidence_paths, root, require_paths=True):
    if not isinstance(evidence_paths, dict):
        return "task %s has invalid evidence_paths" % task_id
    allowed_types = {"files", "commands", "ui"}
    unknown_types = sorted(set(evidence_paths) - allowed_types)
    if unknown_types:
        return "task %s has invalid evidence_paths: %s" % (task_id, ", ".join(unknown_types))
    paths = []
    for evidence_type in ("files", "commands", "ui"):
        entries = evidence_paths.get(evidence_type, [])
        if not isinstance(entries, list) or not all(isinstance(item, str) and item for item in entries):
            return "task %s has invalid %s evidence paths" % (task_id, evidence_type)
        paths.extend((evidence_type, item) for item in entries)
    if require_paths and not paths:
        return "task %s is missing evidence paths" % task_id
    for evidence_type, relative_path in paths:
        try:
            candidate = Path(relative_path)
            if candidate.is_absolute() or ".." in candidate.parts:
                return "task %s has path escape for %s evidence: %s" % (
                    task_id,
                    evidence_type,
                    relative_path,
                )
            resolved = (root / candidate).resolve()
        except PATH_ERRORS:
            return "task %s evidence path could not be validated: %r" % (
                task_id,
                relative_path,
            )
        try:
            resolved.relative_to(root)
        except ValueError:
            return "task %s has path escape for %s evidence: %s" % (
                task_id,
                evidence_type,
                relative_path,
            )
        try:
            if not resolved.is_file():
                return "task %s has missing evidence: %s" % (task_id, relative_path)
            if resolved.stat().st_size == 0:
                return "task %s has empty evidence: %s" % (task_id, relative_path)
        except PATH_ERRORS:
            return "task %s evidence path could not be validated: %r" % (
                task_id,
                relative_path,
            )
    return None


def handle_stop(ledger, cwd):
    root = ledger_root(ledger, cwd)
    if root is None:
        block(LEDGER_ROOT_ERROR)
        return
    tasks = ledger["tasks"]
    for task_id, task in tasks.items():
        shape_error = task_shape_error(task)
        if shape_error:
            block("task %s is invalid: %s" % (task_id, shape_error))
            return
        if task.get("status") != "accepted":
            continue
        dependencies = task["dependencies"]
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
        if (
            not isinstance(accepted, dict)
            or not isinstance(accepted.get("by"), str)
            or not accepted["by"].strip()
            or not isinstance(accepted.get("at"), str)
            or not accepted["at"].strip()
        ):
            block("task %s is missing accepted metadata" % task_id)
            return
        error = evidence_error(task_id, task.get("evidence_paths"), root)
        if error:
            block(error)
            return


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"PreToolUse", "SubagentStop", "Stop"}:
        return 0
    if sys.argv[1] == "PreToolUse":
        payload = read_input()
        if payload is not None and not is_marked_spawn(payload):
            return 0
        try:
            cwd = Path.cwd()
        except PATH_ERRORS:
            deny_pretool(HOOK_CWD_ERROR)
            return 0
        ledger, ledger_error = load_ledger(cwd)
        if ledger is None:
            if ledger_error:
                deny_pretool(ledger_error)
            return 0
        if payload is None:
            deny_pretool("hook input must be valid JSON")
            return 0
        handle_pretooluse(ledger, payload)
        return 0
    try:
        cwd = Path.cwd()
    except PATH_ERRORS:
        block(HOOK_CWD_ERROR)
        return 0
    ledger, ledger_error = load_ledger(cwd)
    if ledger is None:
        if ledger_error:
            block(ledger_error)
        return 0
    payload = read_input()
    if payload is None:
        block("hook input must be valid JSON")
        return 0
    if sys.argv[1] == "SubagentStop":
        handle_subagentstop(ledger, payload, cwd)
    else:
        handle_stop(ledger, cwd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
