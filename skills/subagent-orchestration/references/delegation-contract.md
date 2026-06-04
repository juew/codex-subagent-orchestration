# Delegation Contract Template

Use this template when assigning work to a subagent.

```markdown
## Assignment

Agent:
Task ID:
Reasoning level / execution mode:

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
Can close/delete this subagent after acceptance?:
Recommended next step:
```
