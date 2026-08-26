---
name: subagent-orchestration
description: Use for long-running or multi-agent Codex work needing a main controller, bounded subagents, delegation, handoffs, acceptance gates, evidence verification, artifact consistency, or cleanup. Consider for 主控/子 Agent, 主控制定计划, agent 实际操作测试, delegated-testing, 任务拆分, 评审/审核/走读, server/page regression, 业务流程测试, 验收测试, UI/API/DB evidence, coverage matrix, and PASS/FAIL/BLOCKED reports.
---

# Subagent Orchestration

This skill does not replace skill selection. Use `superpowers:using-superpowers` or the host platform's skill-discovery rules first. Invoke this skill only after the work is classified as long-running, multi-agent, handoff-sensitive, artifact-consistency-heavy, or deliverable-oriented work that needs a main controller, acceptance gates, evidence verification, or strict output-quality control.

Use this skill to run reliable long-running work with one main controller and one or more bounded subagents. The main controller owns planning, delegation, acceptance, permissions, handoffs, and final consistency. Subagents execute scoped tasks and return evidence for acceptance.

## Testing And Acceptance Trigger

After `superpowers:using-superpowers` performs the first process-skill decision, invoke this skill for testing or acceptance work when the prompt includes two or more of these signals:

- Server/page regression, 服务器页面回归, 巡检, 验收测试, 业务流程测试, acceptance testing, release verification, or batch regression.
- UI/browser evidence plus API, DB, fixture, log, or code evidence.
- Multiple roles, modules, pages, task slices, or independent coverage dimensions.
- A coverage matrix, PASS/FAIL/BLOCKED report, screenshots, JSON evidence, reproduction paths, or defect ledger.
- A user expects 主控, 子 Agent, evidence acceptance, handoff, or final consistency across artifacts.

Testing and acceptance work defaults to `delegated-testing`: the main controller plans coverage, assigns bounded test slices, enforces evidence gates, accepts or rejects results, and writes the final conclusion. A UI/test subagent performs the actual browser, role-switching, page-clicking, screenshot, API probe, or data-preparation task when the platform provides a suitable subagent/tool path. The main controller may operate the UI directly only for a minimal preflight, to inspect or reproduce subagent evidence, or when no subagent/tooling path can perform the action; record that exception in the ledger.

For shared browser or UI surfaces, keep one active UI operator. By default that operator should be a delegated UI/test subagent, not the main controller. Other subagents may handle static mapping, data preparation, API checks, report drafting, and evidence review only when their scopes do not conflict.

If the user says 主控制定计划, agent 实际操作测试, 子 Agent 执行测试, 主控不要实操, or asks why the main controller is operating the page, treat that as a hard boundary: stop main-controller UI execution, preserve the current browser/test state, delegate the next test action to a UI/test subagent, and return the main controller to planning, monitoring, acceptance, and final reporting.

## Role Contract

- The main controller owns the objective, task breakdown, acceptance criteria, state ledger,
  tool-policy decisions, risk calls, and final response. It does **not** own the user's
  authorization boundary — see Authorization Boundary.
- A subagent owns only its assigned scope. It must not expand scope, make final product decisions, or mutate shared artifacts unless the delegation explicitly allows it.
- A subagent returning `READY_FOR_ACCEPTANCE` means "please inspect my evidence"; it does not mean the task is complete.
- The main controller must independently verify subagent outputs before marking work complete or allowing downstream tasks to depend on them.
- Reuse a capable subagent for continuity by default. Spawn a new subagent only after a reuse gate records why existing agents are unsuitable.
- A newly spawned subagent starts without another subagent's loaded skills, references, tool state, artifact knowledge, or local assumptions unless the main controller explicitly supplies them in the assignment or handoff.
- Replace or close a subagent when it shows context pollution, repeated misinterpretation, stale assumptions, tool-policy violations, role drift, or a missing required capability.
- Do not leave idle subagents open for convenience. Once their final status, evidence, and any required handoff are captured, request close/delete with the platform's lifecycle tool.

## Execution Boundary

Classify the controller's execution mode before delegating:

- `review-only`: inspect, coordinate, and report. Do not edit business code, create commits, push, deploy, or run destructive commands.
- `plan-handoff`: turn reviewed findings into an implementation plan, task ledger, acceptance criteria, or prompts for later implementation agents. Do not implement the tasks.
- `delegated-testing`: execute acceptance or regression tests through bounded subagents. The main controller owns the test plan, ledger, evidence contract, acceptance gates, final consistency, and final verdict; UI/test subagents perform the actual browser/API/data actions unless an explicit exception is recorded.
- `delegated-implementation`: implement after explicit user authorization, but implementation work is assigned to subagents. The main controller plans, delegates, reviews evidence, resolves conflicts, runs or requests verification, and decides acceptance; it does not directly edit business code.
- `controller-implementation`: the main controller may directly edit files only when the user explicitly authorizes the controller itself to implement, or when the edit is limited to orchestration artifacts such as ledgers, handoffs, prompts, or verification notes.

Use `review-only` when the prompt says 架构师, 走读, 审核, 审计, 评审, 只读, 提出修改建议, 给产品看看, or asks for a report. Use `plan-handoff` when the prompt asks for 实施清单, 修改路线图, 任务拆分, or 给后续实现/开发 Agent. Do not reinterpret short follow-ups such as "请开始", "继续", or "好了" as permission to implement if the active mode is review-only or plan-handoff.

Before entering implementation, require an explicit instruction such as "开始改代码", "请实现", "在当前分支落地这些改动", or another unambiguous request to modify code. Under this skill, default implementation mode is `delegated-implementation`: subagents write business code and the controller verifies. Escalate to `controller-implementation` only when the user explicitly says the main controller should make the code edits itself or when no subagent/tooling path is available and the user confirms that exception.

If the user says 严格使用 subagent-orchestration, 子 Agent 完成, 主控不要自己干活, or asks why the controller is editing, treat that as a hard boundary: stop direct business-code edits immediately, preserve the worktree, delegate the remaining implementation to a subagent, and switch the controller back to planning, acceptance, conflict resolution, and final reporting.

## Authorization Boundary

The controller decides how work is delegated. It does not decide what the user has
consented to. These are different powers, and conflating them is the failure this
section exists to prevent.

- **A controller message is not user consent.** Relaying "the user approved this" is
  hearsay to the receiving subagent. For changes to permission rules, hook wiring,
  credentials, or any configuration that grants standing authority, the subagent is
  right to refuse and ask for the user's own words. Treat such a refusal as correct
  behaviour, not obstruction, and do not re-issue the instruction with more emphasis.
- **Consent is scoped to what was known when it was given.** If a material property is
  discovered mid-task that the user could not have known — a capability the change also
  grants, a side effect, a cost — the earlier authorization does not cover it. Stop,
  state the new fact plainly, and ask again. "They already said yes" is not an answer to
  "yes to what?"
- **Capability-granting and capability-reducing changes are not equivalent.** Removing a
  hook, tightening a rule, or deleting an entry can proceed on ordinary task
  authorization. Adding one that lets something act without a prompt needs the user
  directly. Split a change along this line when it has both halves; the safe half can
  land while the other waits.
- **Record the refusal, not just the outcome.** A subagent that halts on authorization
  grounds has produced a finding. Put it in the ledger with the fact that triggered it,
  so the decision is reviewable later.

## Main Workflow

1. Classify the work: review-only, plan-handoff, delegated-implementation, controller-implementation, artifact editing, investigation, or closure.
2. Create a state ledger for nontrivial work at `<cwd>/.codex/subagent-orchestration/ledger.json`. Set its `root` to that same current hook workspace (`<cwd>`); the resolved root must equal the hook process current working directory. Track owner `agent_id`, task, status, dependencies, `skills_required`, `tools_required`, inputs, outputs, blockers, artifact paths, acceptance status, and next step. Use `references/hook-evidence-contract.md` and [`../../schemas/ledger.schema.json`](../../schemas/ledger.schema.json).
3. Define task slices with clear boundaries. Only parallelize tasks whose write sets, UI surfaces, and dependencies do not conflict.
4. Run the reuse gate before spawning any subagent. Reuse an existing suitable subagent with `send_input`; spawn only with a recorded reason.
5. Delegate using a written contract. Include goal, scope, reuse decision, prior context or handoff, allowed tools, forbidden actions, expected evidence, output format, acceptance criteria, and stop conditions.
6. Monitor without micromanaging. Poll status, inspect new artifacts, and update the ledger.
7. Accept or reject outputs. Reject outputs that lack evidence, violate tool policy, contradict source facts, or are inconsistent with other artifacts.
8. Write handoffs before context becomes fragile.
9. Retire or request close for subagents that are accepted, blocked with handoff, failed, canceled, or superseded.
10. For normal completion, close only after accepted outputs, final consistency checks, and subagent cleanup. After a `wait_agent` timeout, output the final conclusion first and make cleanup best-effort.

## Subagent Reuse And Continuity

Treat reuse as the default path. Creating another subagent is a decision that needs justification.

- Before every `spawn_agent`, inspect the ledger for active, paused, or recently retired subagents whose scope, loaded skills, references, tools, artifact knowledge, and accepted facts match the next task.
- Reuse an existing subagent with `send_input` when the next task depends on that subagent's context, prior investigation, loaded skill instructions, checked artifacts, or unresolved assumptions.
- Spawn a new subagent only when the task is independent and parallelizable, requires a clearly different role or capability, has a disjoint write boundary, the prior subagent is closed/unavailable, or the prior subagent is polluted, stale, drifting, blocked, or missing required tools.
- Record a reuse decision in the ledger for every assignment: `reused <agent-id>` or `spawned new because <reason>`.
- Track a compact capability/context card per subagent: id, nickname, assigned scope, active skills or references loaded, allowed tools, artifact paths inspected, accepted facts, unresolved assumptions, write boundary, reuse eligibility, and cleanup status.
- Do not assume a new subagent knows what a previous subagent knew. If replacing or splitting work, pass the relevant handoff, accepted facts, artifact paths, required skills, and tool-policy constraints explicitly.
- Do not spawn multiple agents for adjacent follow-up questions when one existing capable agent can continue without conflicting writes or context risk.
- If a subagent is retained for likely follow-up, record why it stays active and when it should be retired.

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

For a ledgered assignment, include `ORCHESTRATION_TASK_ID: <id>` in the assignment text and pass every required skill as a structured item with `type: "skill"` and its ledger name. The plugin's `PreToolUse` hook denies marked `spawn_agent` calls that omit one. The subagent's final line must be the single JSON `ORCHESTRATION_REPORT:` proof in `references/hook-evidence-contract.md`; `SubagentStop` blocks a malformed, mismatched, or incomplete proof.

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
- It proves the artifact exists but not that it takes effect.

Accepted evidence should be traceable from task to source material, change, verification result, and final artifact.

**Existence is not activation.** For any change whose value depends on being *in force* —
a hook, a registration, a permission rule, a feature flag, a scheduled job, a config
entry — reading the file back is not evidence. It proves the write happened, not that
anything behaves differently now. Require an observation of the effect: exercise the
trigger and inspect the side effect. A cheap general method is a sentinel — have the
change also append a timestamped line to a file, exercise the trigger, confirm the line,
then remove the sentinel and confirm the removal. Reject `READY_FOR_ACCEPTANCE` for this
class of change when the only evidence is file content, a directory listing, or a status
field. A registry reporting something as `loaded`, `installed`, or `enabled` is a claim
about registration, not about execution; the two diverge whenever activation is deferred
to the next session, reload, or restart.

For every controller-accepted task, record `skills_loaded`, `tools_proven`, accepted metadata, and relative evidence paths before setting `status` to `accepted`. The `Stop` hook verifies dependency acceptance, required coverage, and non-empty evidence files beneath the current hook workspace recorded as the ledger root. Hooks are read-only and silently no-op when the fixed ledger path is absent.

When the status event is missing or delayed, sufficient inspected evidence may satisfy acceptance. Record the missing event as a warning instead of waiting indefinitely for a status update.

## Tool Policy Enforcement

When a user or task requires specific tools, treat that requirement as a hard acceptance gate.

- Put required tools in the delegation contract.
- Require subagents to report which tool performed the key action and which tool produced evidence.
- If a required tool is unavailable, the human-readable blocker may say `BLOCKED_REQUIRED_TOOL_UNAVAILABLE`, but the final `ORCHESTRATION_REPORT` status must be `BLOCKED`. Report the actual, possibly partial or empty, `skills_loaded` and `tools_proven` arrays.
- If a screenshot or artifact is produced by a fallback path, it must be labeled as fallback or diagnostic.
- The main controller must reject `READY_FOR_ACCEPTANCE` when required skill or tool usage is not proven. Full ledger requirement coverage is enforced for `READY_FOR_ACCEPTANCE`; `BLOCKED`, `FAIL`, and `NEEDS_CLARIFICATION` still require structurally valid proof arrays but may report partial or empty actual proof.

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
