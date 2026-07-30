# Delegation Contract Template

Use this template when assigning work to a subagent (as the `Agent` tool prompt, or a `SendMessage` follow-up to a reused agent).

```markdown
## Assignment

Agent (name/type):
Task ID:
Reasoning level / execution mode:
Reuse decision (reused <agent-name> | spawned new because <reason>):

## Objective

Complete:
Do not complete:

## Scope

Allowed files/systems/UI:
Forbidden files/systems/UI:
Write boundary (worktree isolation? output path?):

## Inputs

References:
Artifacts:
Prior accepted decisions:
Prior subagent context or handoff:
Required skills or references to load:

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
Reusable for follow-up (via SendMessage)?:
Recommended next step:
```
