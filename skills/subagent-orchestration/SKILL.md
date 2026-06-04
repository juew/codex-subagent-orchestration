---
name: subagent-orchestration
description: Use this skill for long-running or multi-agent Codex work where a main controller must coordinate bounded subagents, acceptance gates, context-budget handoffs, tool-use policy, artifact consistency, safe resumption, or subagent lifecycle cleanup after pauses, blocking, cancellation, or completion.
---

# Subagent Orchestration

This skill does not replace skill selection. Use `superpowers:using-superpowers` or the host platform's skill-discovery rules first; invoke this skill only after the work is classified as long-running, multi-agent, or handoff-sensitive.

Use this skill to run reliable long-running work with one main controller and one or more bounded subagents. The main controller owns planning, delegation, acceptance, permissions, handoffs, and final consistency. Subagents execute scoped tasks and return evidence for acceptance.

## Role Contract

- The main controller owns the objective, task breakdown, acceptance criteria, state ledger, permission decisions, risk calls, and final response.
- A subagent owns only its assigned scope. It must not expand scope, make final product decisions, or mutate shared artifacts unless the delegation explicitly allows it.
- A subagent returning `READY_FOR_ACCEPTANCE` means "please inspect my evidence"; it does not mean the task is complete.
- The main controller must independently verify subagent outputs before marking work complete or allowing downstream tasks to depend on them.
- Prefer reusing a capable subagent for continuity. Replace or close it when it shows context pollution, repeated misinterpretation, stale assumptions, tool-policy violations, or role drift.
- Do not leave idle subagents open for convenience. Once their final status, evidence, and any required handoff are captured, close/delete them with the platform's lifecycle tool.

## Main Workflow

1. Classify the work: plan-only, execution, review, artifact editing, investigation, or closure.
2. Create a state ledger for nontrivial work. Track owner, task, status, inputs, outputs, blockers, artifact paths, acceptance status, and next step.
3. Define task slices with clear boundaries. Only parallelize tasks whose write sets, UI surfaces, and dependencies do not conflict.
4. Delegate using a written contract. Include goal, scope, allowed tools, forbidden actions, expected evidence, output format, acceptance criteria, and stop conditions.
5. Monitor without micromanaging. Poll status, inspect new artifacts, and update the ledger.
6. Accept or reject outputs. Reject outputs that lack evidence, violate tool policy, contradict source facts, or are inconsistent with other artifacts.
7. Write handoffs before context becomes fragile.
8. Retire or close subagents that are accepted, blocked with handoff, failed, canceled, or superseded.
9. Close only after accepted outputs, final consistency checks, and subagent cleanup.

## Subagent Lifecycle And Cleanup

Treat subagent cleanup as part of orchestration, not as optional housekeeping.

- Track every subagent in the ledger as `active`, `accepted`, `blocked-handoff-written`, `failed`, `canceled`, `superseded`, or `closed`.
- Keep a subagent active only while it is doing useful work or while the main controller is waiting for evidence needed on the critical path.
- After accepting a result, record the evidence and changed artifacts, then close/delete the subagent unless immediate follow-up requires the same context.
- Before closing a blocked, paused, or superseded subagent, capture a handoff or explicit non-handoff reason.
- If a platform distinguishes close, archive, delete, and cancel, use the least destructive action that stops the agent from accumulating as active state.
- In Codex multi-agent sessions, call `multi_agent_v1.close_agent` for subagents that no longer need `send_input` or `wait_agent`; use `resume_agent` only when a closed agent's context is genuinely needed again.
- Do not create replacement subagents until the old one is marked `superseded` and closed, unless both must briefly overlap for a bounded handoff.

## Delegation Contract

Every subagent assignment should include:

- Objective: the concrete outcome.
- Scope: exactly what may be changed, clicked, edited, tested, or inspected.
- Inputs: file paths, references, issue IDs, URLs, screenshots, prior decisions, and required constraints.
- Allowed tools: required tools and preferred tools.
- Forbidden actions: destructive operations, unapproved environments, shared files, secret values, or unrelated scope.
- Evidence: logs, screenshots, diffs, rendered previews, command output, or structured findings.
- Stop conditions: `READY_FOR_ACCEPTANCE`, `BLOCKED`, `FAIL`, `NEEDS_CLARIFICATION`, or task-specific checkpoints.
- Return format: concise status, artifacts changed, evidence paths, open risks, and next recommended action.

See `references/delegation-contract.md` for a reusable template.

## Acceptance Gates

The main controller must reject a subagent result when:

- It does not address the assigned scope.
- It changed files or systems outside the assignment.
- It lacks required evidence or tool-use proof.
- It used a forbidden tool or skipped a required tool.
- It records conclusions that are not supported by evidence.
- It relies on unaccepted outputs from another subagent.
- It creates inconsistency between final artifacts.

Accepted evidence should be traceable from task to source material, change, verification result, and final artifact.

## Tool Policy Enforcement

When a user or task requires specific tools, treat that requirement as a hard acceptance gate.

- Put required tools in the delegation contract.
- Require subagents to report which tool performed the key action and which tool produced evidence.
- If a required tool is unavailable, the subagent must return `BLOCKED_REQUIRED_TOOL_UNAVAILABLE`.
- If a screenshot or artifact is produced by a fallback path, it must be labeled as fallback or diagnostic.
- The main controller must reject `READY_FOR_ACCEPTANCE` when required tool usage is not proven.

For UI tasks, separate operation evidence from formal evidence. A whole-screen diagnostic screenshot may help debugging, but it is not automatically formal evidence.

## Context Budget And Handoff

Write a handoff before context becomes unreliable, not after it fails.

Create a handoff when any of these are true:

- The task is long-running or likely to continue after context compaction.
- A subagent is paused, blocked, replaced, or finished at a checkpoint.
- Many artifacts, external states, decisions, or open risks exist.
- A rule changed, a conclusion was withdrawn, or the task was remapped.
- Future agents need exact continuation steps.

A handoff must include:

- Current objective and scope.
- Completed work.
- Unfinished work.
- Current state and blockers.
- Active or retired subagents.
- Key artifact paths.
- Accepted facts.
- Unverified assumptions.
- Latest user instructions and preferences.
- Forbidden actions.
- Next recommended steps.

Subagent handoffs cover only the subagent's scope. Main-controller handoffs summarize global state.

See `references/handoff-template.md` for a compact template.

## Parallelism Rules

Parallelize only when all conditions hold:

- Tasks do not operate the same UI, process, branch, database, or external object.
- Tasks do not write the same file or artifact.
- No task depends on another task's unaccepted result.
- Each subagent has a separate output path or write boundary.

Use one active UI operator per shared UI surface. Use document or review agents in parallel only if their write sets are separate or read-only.

## Artifact Consistency

For work with multiple final artifacts, the main controller must run a final consistency pass:

- Counts and statuses match across artifacts.
- IDs and names use the same mapping everywhere.
- Defects, issues, or blockers have either a registered record or an explicit non-registration reason.
- Withdrawn decisions do not remain as active conclusions.
- Final user-facing results match accepted evidence and latest user decisions.

## Closure

Do not close a long-running task until:

- Every active subtask is accepted, blocked with a handoff, or explicitly canceled.
- Every subagent that no longer needs interaction has been closed/deleted or has a recorded reason for staying active.
- Shared artifacts are consistent.
- Required verification commands or visual checks have run.
- The final answer states what changed, what was verified, and any remaining risk.
