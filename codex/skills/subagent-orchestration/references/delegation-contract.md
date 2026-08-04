# Delegation Contract Template

Use this template when assigning work to a subagent.

```markdown
## Assignment

Agent:
Task ID:
Agent ID recorded in ledger:
Reasoning level / execution mode:
Reuse decision:

## Objective

Complete:
Do not complete:

## Scope

Allowed files/systems/UI:
Forbidden files/systems/UI:
Write boundary:

## Inputs

References:
Artifacts:
Prior accepted decisions:
Prior subagent context or handoff:
Required skills or references already loaded:

## Ledger And Hook Contract

Ledger path: `<cwd>/.codex/subagent-orchestration/ledger.json`
Assignment marker: `ORCHESTRATION_TASK_ID: <Task ID>`
Structured skill items: one `{ "type": "skill", "name": "<required skill>" }` entry for every `skills_required` value.
Ledger root and evidence contract: `references/hook-evidence-contract.md`

## Required Tools

Must use:
May use:
Forbidden:

## Evidence Required

Screenshots/logs/diffs:
Tool-use proof:
Verification command or check:

## Stop Conditions

Return `READY_FOR_ACCEPTANCE` when:
Return `BLOCKED` when:
Return `FAIL` when:
Return `NEEDS_CLARIFICATION` when:

## Return Format

Status:
Changed artifacts:
Evidence paths:
Risks:
Reusable for follow-up?:
Can close/delete this subagent after acceptance?:
Close confirmation status:
Cleanup warnings:
Status-event warnings:
Recommended next step:

Final line (required):
`ORCHESTRATION_REPORT: {"task_id":"<Task ID>","status":"READY_FOR_ACCEPTANCE","skills_loaded":["<skill>"],"tools_proven":["<tool>"],"evidence_paths":{"commands":["evidence/tests.log"]}}`
```
