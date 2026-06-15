---
name: subagent-orchestration
description: Use this skill for long-running or multi-agent Codex work where a main controller must coordinate bounded subagents, task slices, acceptance gates, context-budget handoffs, tool-use policy, artifact consistency, evidence verification, safe resumption, strict output-quality control, or subagent lifecycle cleanup after pauses, blocking, cancellation, or completion. Strongly consider it for 架构师 Agent, 主控 Agent, 走读, 审核, 审计, 评审, 实施清单, 修改建议, 任务拆分, 后续实现 Agent, 交给开发 Agent, 子 Agent 完成, 主控不要自己干活, 主控不直接写代码, or other review-to-handoff and delegated-implementation workflows where the controller should produce evidence-backed plans, delegate implementation, and enforce acceptance gates before code is changed or accepted. Also consider it for concrete deliverables such as 报告, PPT, Excel, 网页, 图片, 代码, 测试证据, or release packages that require 主控, 验收标准, 验证节点, 产物一致性, or cross-artifact quality control after superpowers:using-superpowers performs the first process-skill decision.
---

# Subagent Orchestration

This skill does not replace skill selection. Use `superpowers:using-superpowers` or the host platform's skill-discovery rules first. Invoke this skill only after the work is classified as long-running, multi-agent, handoff-sensitive, artifact-consistency-heavy, or deliverable-oriented work that needs a main controller, acceptance gates, evidence verification, or strict output-quality control.

Use this skill to run reliable long-running work with one main controller and one or more bounded subagents. The main controller owns planning, delegation, acceptance, permissions, handoffs, and final consistency. Subagents execute scoped tasks and return evidence for acceptance.

## Role Contract

- The main controller owns the objective, task breakdown, acceptance criteria, state ledger, permission decisions, risk calls, and final response.
- A subagent owns only its assigned scope. It must not expand scope, make final product decisions, or mutate shared artifacts unless the delegation explicitly allows it.
- A subagent returning `READY_FOR_ACCEPTANCE` means "please inspect my evidence"; it does not mean the task is complete.
- The main controller must independently verify subagent outputs before marking work complete or allowing downstream tasks to depend on them.
- Prefer reusing a capable subagent for continuity. Replace or close it when it shows context pollution, repeated misinterpretation, stale assumptions, tool-policy violations, or role drift.
- Do not leave idle subagents open for convenience. Once their final status, evidence, and any required handoff are captured, request close/delete with the platform's lifecycle tool.

## Execution Boundary

Classify the controller's execution mode before delegating:

- `review-only`: inspect, coordinate, and report. Do not edit business code, create commits, push, deploy, or run destructive commands.
- `plan-handoff`: turn reviewed findings into an implementation plan, task ledger, acceptance criteria, or prompts for later implementation agents. Do not implement the tasks.
- `delegated-implementation`: implement after explicit user authorization, but implementation work is assigned to subagents. The main controller plans, delegates, reviews evidence, resolves conflicts, runs or requests verification, and decides acceptance; it does not directly edit business code.
- `controller-implementation`: the main controller may directly edit files only when the user explicitly authorizes the controller itself to implement, or when the edit is limited to orchestration artifacts such as ledgers, handoffs, prompts, or verification notes.

Use `review-only` when the prompt says 架构师, 走读, 审核, 审计, 评审, 只读, 提出修改建议, 给产品看看, or asks for a report. Use `plan-handoff` when the prompt asks for 实施清单, 修改路线图, 任务拆分, or 给后续实现/开发 Agent. Do not reinterpret short follow-ups such as "请开始", "继续", or "好了" as permission to implement if the active mode is review-only or plan-handoff.

Before entering implementation, require an explicit instruction such as "开始改代码", "请实现", "在当前分支落地这些改动", or another unambiguous request to modify code. Under this skill, default implementation mode is `delegated-implementation`: subagents write business code and the controller verifies. Escalate to `controller-implementation` only when the user explicitly says the main controller should make the code edits itself or when no subagent/tooling path is available and the user confirms that exception.

If the user says 严格使用 subagent-orchestration, 子 Agent 完成, 主控不要自己干活, or asks why the controller is editing, treat that as a hard boundary: stop direct business-code edits immediately, preserve the worktree, delegate the remaining implementation to a subagent, and switch the controller back to planning, acceptance, conflict resolution, and final reporting.

## Main Workflow

1. Classify the work: review-only, plan-handoff, delegated-implementation, controller-implementation, artifact editing, investigation, or closure.
2. Create a state ledger for nontrivial work. Track owner, task, status, inputs, outputs, blockers, artifact paths, acceptance status, and next step.
3. Define task slices with clear boundaries. Only parallelize tasks whose write sets, UI surfaces, and dependencies do not conflict.
4. Delegate using a written contract. Include goal, scope, allowed tools, forbidden actions, expected evidence, output format, acceptance criteria, and stop conditions.
5. Monitor without micromanaging. Poll status, inspect new artifacts, and update the ledger.
6. Accept or reject outputs. Reject outputs that lack evidence, violate tool policy, contradict source facts, or are inconsistent with other artifacts.
7. Write handoffs before context becomes fragile.
8. Retire or request close for subagents that are accepted, blocked with handoff, failed, canceled, or superseded.
9. For normal completion, close only after accepted outputs, final consistency checks, and subagent cleanup. After a `wait_agent` timeout, output the final conclusion first and make cleanup best-effort.

## Subagent Lifecycle And Cleanup

Treat subagent cleanup as part of orchestration, not as optional housekeeping.

- Track every subagent in the ledger as `active`, `accepted`, `blocked-handoff-written`, `failed`, `canceled`, `superseded`, `wait-timeout`, `status-event-missing-evidence-accepted`, `close-requested`, `closed`, `close-requested-unconfirmed-warning`, `close-failed-warning`, or `cleanup-warning`.
- Keep a subagent active only while it is doing useful work or while the main controller is waiting for evidence needed on the critical path.
- Before final output, run at most one bounded wait-drain for subagents whose results could still affect the critical path. Do not repeatedly call `wait_agent` just to classify stale, non-critical, or cleanup-only agents.
- After accepting a result, record the evidence and changed artifacts, then request close/delete for the subagent unless immediate follow-up requires the same context.
- If a completion/status event is missing or delayed but artifacts, diffs, logs, screenshots, or other evidence are sufficient to verify the assigned scope, accept the result as `status-event-missing-evidence-accepted` and report the missing status event as a warning.
- Before closing a blocked, paused, or superseded subagent, capture a handoff or explicit non-handoff reason.
- If a platform distinguishes close, archive, delete, and cancel, use the least destructive action that stops the agent from accumulating as active state.
- In Codex multi-agent sessions, call `multi_agent_v1.close_agent` for subagents that no longer need `send_input` or `wait_agent`; use `resume_agent` only when a closed agent's context is genuinely needed again.
- If `wait_agent` times out, produce the final user-facing conclusion before cleanup. Treat `close_agent` after a wait timeout as best-effort only, with at most one close attempt per affected subagent unless the user explicitly asks to wait.
- Treat `close_agent` as idempotent best-effort cleanup, not as a required deletion acknowledgment. If close confirmation is missing, duplicated, delayed, or failed, record one terminal warning state per subagent and continue.
- Do not create replacement subagents until the old one is marked `superseded` and either `closed` or recorded as a terminal cleanup warning such as `close-requested-unconfirmed-warning` or `close-failed-warning`, unless both must briefly overlap for a bounded handoff.

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

When the status event is missing or delayed, sufficient inspected evidence may satisfy acceptance. Record the missing event as a warning instead of waiting indefinitely for a status update.

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

- Every subtask is accepted, blocked with a handoff, explicitly canceled, accepted as `status-event-missing-evidence-accepted`, or recorded as `wait-timeout` with the missing result disclosed as a risk.
- Every subagent that no longer needs interaction has been closed/deleted, has cleanup requested, has a terminal cleanup warning, or has a recorded reason for staying active. After a `wait_agent` timeout, this check becomes best-effort cleanup after the final conclusion, with cleanup failures reported as warnings.
- Shared artifacts are consistent.
- Required verification commands or visual checks have run.
- The final answer states what changed, what was verified, and any remaining risk.
