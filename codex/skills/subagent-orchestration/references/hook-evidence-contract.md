# Hook And Evidence Contract

Codex discovers this plugin's command hooks from `hooks/hooks.json`. The handlers expand
`${PLUGIN_ROOT}` themselves and read only `<cwd>/.codex/subagent-orchestration/ledger.json`.
They never create, update, or delete a ledger or evidence artifact. When that ledger is absent,
`PreToolUse`, `SubagentStop`, and `Stop` succeed silently with no output.

## Hook Trust

Hooks execute the plugin's checked-in Python command handler during Codex events. Before
installation, inspect the checked-in `hooks/hooks.json` and `scripts/verify_ledger.py` source; the
handlers are read-only, but deterministic enforcement is executable code rather than instruction
text. After installing the complete plugin, open Codex `/hooks`, open this plugin's installed hook
configuration, review it, and trust and enable its handlers there. Deterministic enforcement does
not run until that post-install enablement; copying the skill alone supplies instructions only.

Use [the JSON schema](../../../schemas/ledger.schema.json) as the ledger shape. The ledger root
must be an existing absolute workspace directory. Evidence paths are always relative to that root.

## Controller Ledger

Each task entry needs an `agent_id`, `status`, `dependencies`, `skills_required`, and
`tools_required`. A controller changes a completed task to `status: "accepted"` only after it
writes all of these fields:

```json
{
  "skills_loaded": ["superpowers:test-driven-development"],
  "tools_proven": ["playwright"],
  "accepted": {"by": "controller", "at": "2026-08-04T00:00:00Z"},
  "evidence_paths": {
    "files": ["evidence/diff.txt"],
    "commands": ["evidence/tests.log"],
    "ui": ["evidence/screenshot.png"]
  }
}
```

`files`, `commands`, and `ui` may be empty when that evidence class does not apply, but at least
one evidence path is required. Every listed path must resolve below `root`, exist as a regular
file, and contain bytes. `Stop` blocks until all accepted tasks have accepted dependencies,
required skill and tool coverage, accepted metadata, and valid evidence.

## PreToolUse

For a `spawn_agent` call, place this exact marker in its assignment text:

```text
ORCHESTRATION_TASK_ID: task-1
```

Also pass every required skill through the structured `items` list; naming a skill in prose is
not enough:

```json
{
  "items": [
    {"type": "skill", "name": "superpowers:test-driven-development"}
  ]
}
```

Unmarked and non-`spawn_agent` calls are allowed. A marked call with a missing ledger task or
structured skill item is denied with Codex's `hookSpecificOutput` contract.

## SubagentStop

The task owner is determined mechanically from `agent_id`. An unrelated agent is allowed. The
matching subagent's final message must end with exactly one line of this form:

```text
ORCHESTRATION_REPORT: {"task_id":"task-1","status":"READY_FOR_ACCEPTANCE","skills_loaded":["superpowers:test-driven-development"],"tools_proven":["playwright"],"evidence_paths":{"commands":["evidence/tests.log"]}}
```

`task_id` selects the ledger task and that task's `agent_id` must match the hook agent. `status`
must be `READY_FOR_ACCEPTANCE`, `BLOCKED`, `FAIL`, or `NEEDS_CLARIFICATION`; `skills_loaded` and
`tools_proven` must cover the ledger requirements. `evidence_paths` must be a valid path-group
object. `READY_FOR_ACCEPTANCE` requires at least one relative, regular, non-empty file below the
ledger root; the other terminal statuses may provide no paths. Missing or malformed reports block
using `{"decision":"block","reason":"..."}`.
