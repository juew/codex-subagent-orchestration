---
name: subagent-orchestration
description: Use for long-running or multi-agent work needing a main controller, bounded subagents, delegation, handoffs, acceptance gates, evidence verification, artifact consistency, or cleanup. Consider for 主控/子 Agent, 主控制定计划, agent 实际操作测试, delegated-testing, 任务拆分, 评审/审核/走读, server/page regression, 业务流程测试, 验收测试, UI/API/DB evidence, coverage matrix, and PASS/FAIL/BLOCKED reports.
---

# Subagent Orchestration

This skill does not replace skill selection. Follow the host platform's normal skill-discovery rules first. Invoke this skill only after the work is classified as long-running, multi-agent, handoff-sensitive, artifact-consistency-heavy, or deliverable-oriented work that needs a main controller, acceptance gates, evidence verification, or strict output-quality control.

Use this skill to run reliable long-running work with one main controller and one or more bounded subagents. The main controller owns planning, delegation, acceptance, permissions, handoffs, and final consistency. Subagents execute scoped tasks and return evidence for acceptance.

## Claude Code Tool Mapping

In Claude Code, orchestration uses these primitives:

- **Spawn a subagent**: the `Agent` tool. Pick `subagent_type` deliberately (`general-purpose` for multi-step work, `Explore` for read-only search, `Plan` for design, or a project-defined agent). Subagents run in the background by default and send a completion notification; pass `run_in_background: false` when the result is needed before continuing.
- **Reuse / continue a subagent**: `SendMessage` with the agent's ID or name continues that agent with its context intact. This is the reuse path — a new `Agent` call always starts cold.
- **Wait / monitor**: rely on completion notifications for background subagents; use `TaskList` / `TaskOutput` to inspect background task state. Never fabricate or predict a pending agent's result.
- **Write isolation**: `isolation: "worktree"` gives a subagent its own git worktree when write boundaries must not overlap.
- **Lifecycle**: Claude Code subagents terminate on their own after returning a final report; there is no explicit close/delete call. "Cleanup" here means updating the ledger to a terminal status and not sending further messages to superseded or polluted agents.
- **Independent verification**: mount `references/evidence-check.md` as an `agent`-type hook on `Stop` or `SubagentStop` in `.claude/settings.json`, so the harness triggers it instead of the controller choosing to. The controller is the party being verified and must not also be the party that decides whether verification runs. Without a hook this degrades to a closure step the controller performs itself; verification is then self-reported and materially weaker.

A subagent's final report is not shown to the user — the main controller must relay what matters.

## Testing And Acceptance Trigger

Invoke this skill for testing or acceptance work when the prompt includes two or more of these signals:

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
- Reuse a capable subagent for continuity by default (`SendMessage` to its ID/name). Spawn a new subagent only after a reuse gate records why existing agents are unsuitable.
- A newly spawned subagent starts without another subagent's loaded skills, references, tool state, artifact knowledge, or local assumptions unless the main controller explicitly supplies them in the assignment or handoff.
- Replace a subagent when it shows context pollution, repeated misinterpretation, stale assumptions, tool-policy violations, role drift, or a missing required capability. Mark the old one `superseded` in the ledger and pass an explicit handoff to the replacement.
- Do not keep messaging idle subagents for convenience. Once their final status, evidence, and any required handoff are captured, record a terminal status and stop interacting with them.

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

1. Classify the work: review-only, plan-handoff, delegated-testing, delegated-implementation, controller-implementation, artifact editing, investigation, or closure.
2. Create a state ledger for nontrivial work (a scratchpad or project file). Track owner, task, status, inputs, outputs, blockers, artifact paths, acceptance status, and next step. Use the schema in `references/ledger-schema.md`. A free-form ledger cannot be verified by a delegated or automated check, and the tool-policy, evidence-tier, and dependency gates below have no checkable meaning without its fields.
3. Define task slices with clear boundaries. Only parallelize tasks whose write sets, UI surfaces, and dependencies do not conflict.
4. Run the reuse gate before spawning any subagent. Reuse an existing suitable subagent with `SendMessage`; spawn a new one with the `Agent` tool only with a recorded reason.
5. Delegate using a written contract. Include goal, scope, reuse decision, prior context or handoff, allowed tools, forbidden actions, expected evidence, output format, acceptance criteria, and stop conditions.
6. Monitor without micromanaging. Watch completion notifications, use `TaskList`/`TaskOutput` for background tasks, inspect new artifacts, and update the ledger.
7. Accept or reject outputs. Reject outputs that lack evidence, violate tool policy, contradict source facts, or are inconsistent with other artifacts.
8. Write handoffs before context becomes fragile.
9. Retire subagents in the ledger once accepted, blocked with handoff, failed, canceled, or superseded.
10. For normal completion, close the task only after accepted outputs, final consistency checks, and ledger cleanup. If a subagent never sends its completion notification but its artifacts are verifiable, output the final conclusion first and record the missing notification as a warning.

## Subagent Reuse And Continuity

Treat reuse as the default path. Creating another subagent is a decision that needs justification.

- Before every `Agent` call, inspect the ledger for active or recently finished subagents whose scope, loaded skills, references, tools, artifact knowledge, and accepted facts match the next task.
- Reuse an existing subagent with `SendMessage` when the next task depends on that subagent's context, prior investigation, loaded skill instructions, checked artifacts, or unresolved assumptions.
- Spawn a new subagent only when the task is independent and parallelizable, requires a clearly different role or capability, has a disjoint write boundary, or the prior subagent is polluted, stale, drifting, blocked, or missing required tools.
- Record a reuse decision in the ledger for every assignment: `reused <agent-name>` or `spawned new because <reason>`.
- Track a compact capability/context card per subagent: name/ID, assigned scope, active skills or references loaded, allowed tools, artifact paths inspected, accepted facts, unresolved assumptions, write boundary, reuse eligibility, and ledger status.
- Do not assume a new subagent knows what a previous subagent knew. If replacing or splitting work, pass the relevant handoff, accepted facts, artifact paths, required skills, and tool-policy constraints explicitly in the new prompt.
- Do not spawn multiple agents for adjacent follow-up questions when one existing capable agent can continue without conflicting writes or context risk.
- If a subagent is retained for likely follow-up, record why it stays listed as reusable and when it should be retired.

## Subagent Lifecycle And Cleanup

Treat subagent bookkeeping as part of orchestration, not as optional housekeeping.

- Track every subagent in the ledger as `active`, `accepted`, `blocked-handoff-written`, `failed`, `canceled`, `superseded`, `notification-pending`, or `evidence-accepted-without-notification`.
- Keep interacting with a subagent only while it is doing useful work or while the main controller is waiting for evidence needed on the critical path.
- Before final output, run at most one bounded check (`TaskList`/`TaskOutput`) for subagents whose results could still affect the critical path. Do not poll repeatedly just to classify stale, non-critical agents — completion notifications arrive on their own.
- After accepting a result, record the evidence and changed artifacts, then mark the subagent's terminal status unless immediate follow-up requires the same context.
- If a completion notification is missing or delayed but artifacts, diffs, logs, screenshots, or other evidence are sufficient to verify the assigned scope, accept the result as `evidence-accepted-without-notification` and report the missing notification as a warning.
- Before superseding a blocked or paused subagent, capture a handoff or explicit non-handoff reason.
- Use `TaskStop` only for a background task that must actually stop (runaway, superseded, or wrong scope) — not as routine cleanup.
- Do not create replacement subagents until the old one is marked `superseded` in the ledger with its handoff captured, unless both must briefly overlap for a bounded handoff.

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

When the completion notification is missing or delayed, sufficient inspected evidence may satisfy acceptance. Record the missing notification as a warning instead of waiting indefinitely.

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
- Each subagent has a separate output path or write boundary (use `isolation: "worktree"` when subagents must write inside the same repo).

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

- Every subtask is accepted, blocked with a handoff, explicitly canceled, accepted as `evidence-accepted-without-notification`, or recorded as `notification-pending` with the missing result disclosed as a risk.
- Every subagent has a terminal ledger status or a recorded reason for staying active/reusable.
- Shared artifacts are consistent.
- Required verification commands or visual checks have run.
- The final answer states what changed, what was verified, and any remaining risk.

Before closing, run the evidence check in `references/evidence-check.md` against the ledger. Delegate it to an independent subagent; the main controller must not substitute its own review for this step. The check is idempotent — tasks with a recorded `check.result` are frozen and not re-verified — so its cost stays flat as the ledger grows. See Claude Code Tool Mapping for the hook-based form, which does not depend on the controller choosing to run it.
