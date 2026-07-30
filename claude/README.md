# Subagent Orchestration

中文 | [English](#english)

## 中文

`subagent-orchestration` 是一个通用 Claude Code skill，用于长流程、多子 agent 的任务编排。它帮助主控 agent 规划任务、分派边界清晰的子任务、设置验收门槛、管理上下文交接、监督工具使用，并在结束前检查所有正式产物的一致性。

适用场景：

- 长时间运行的开发、测试、文档、迁移或审计任务
- 需要多个子 agent 并行或接力完成的任务
- 需要主控统一验收、统一风险判断的任务
- 需要在上下文很长、任务暂停或 agent 替换时写交接文档的任务
- 需要强制执行特定工具策略的任务，例如必须使用某个浏览器、桌面自动化工具或渲染器

核心原则：

- 主控负责计划、分派、权限、验收、状态总账和最终结论。
- 子 agent 只执行被分配的边界任务，不自行扩大范围。
- `READY_FOR_ACCEPTANCE` 只是等待主控验收，不等于任务完成。
- 如果用户把当前 agent 定义为“架构师 / 主控 / 审核 / 走读 / 评审”，默认是只读审查和交接模式；除非用户明确说“开始改代码 / 请实现 / 在当前分支落地”，否则不要把修改建议直接变成代码提交。
- “实施清单、修改路线图、给后续开发 Agent 的任务拆分”属于 plan-handoff 产物，目标是交给后续实现 agent，而不是当前主控直接执行。
- 进入实现阶段后，默认也是 delegated-implementation：子 Agent 写业务代码，主控只负责任务拆分、下发、证据复核、冲突裁决、验收比对和最终报告。只有用户明确要求主控亲自改代码，才进入 controller-implementation。
- 上下文变长、任务暂停、规则变化、结论撤销或 agent 换班时必须写交接文档。
- 如果用户要求某个工具，工具使用证明必须成为验收门槛。

### 编排原语

skill 中的编排动作对应 Claude Code 的以下能力：

| 编排动作 | Claude Code |
|---|---|
| 派生子 agent | `Agent` 工具，按任务选择 `subagent_type` |
| 复用子 agent | `SendMessage`，按 agent 名称或 ID 延续其上下文 |
| 等待与监控 | 后台完成通知，配合 `TaskList` / `TaskOutput` |
| 写边界隔离 | `isolation: "worktree"` |
| 生命周期收尾 | 子 agent 返回最终报告后自行终止，总账置终态即可 |

需要注意：子 agent 的最终报告不会直接展示给用户，主控必须转述关键结论。

### 何时启用

不要把 `subagent-orchestration` 作为所有任务的默认入口；小任务强行启用会增加文书和协调成本。

```text
是否需要多个执行者、多个产物、跨上下文延续、独立验收、或多证据测试回归？
是 -> subagent-orchestration
否 -> 直接做，或使用对应的领域 skill
```

推荐启动话术：

```text
如果当前角色是架构师/审核/主控，请保持 review-only 或 plan-handoff。
收到明确实现授权后，默认进入 delegated-implementation：
子 Agent 写业务代码，主控只做编排、复核、裁决和验收。
```

建议和领域 skill 配合使用；领域规则保留在对应领域 skill 中。

## English

`subagent-orchestration` is a general-purpose Claude Code skill for long-running work that uses a main controller and bounded subagents. It helps the controller plan work, delegate scoped tasks, enforce acceptance gates, manage context handoffs, supervise required tool usage, and verify final artifact consistency.

Use it for:

- Long-running development, testing, documentation, migration, or audit work
- Multi-agent workflows with parallel or sequential subagents
- Tasks where one controller must own acceptance, risk decisions, and final status
- Work that needs handoff documents before context compaction, pauses, or agent replacement
- Work with strict tool-use policies, such as required browser, desktop automation, or rendering tools

Core principles:

- The controller owns planning, delegation, permissions, acceptance, the state ledger, and final conclusions.
- Subagents execute only their assigned bounded tasks.
- `READY_FOR_ACCEPTANCE` means the result is waiting for controller review, not that the task is complete.
- If the user defines the current agent as an architect, controller, auditor, reviewer, or code-walk agent, default to review-only or handoff mode. Do not turn recommendations into code commits unless the user explicitly says to implement, change code, or land the work on the current branch.
- Implementation plans, roadmaps, and tasks for later development agents are plan-handoff artifacts, not permission for the current controller to execute them.
- After implementation is authorized, default to delegated-implementation: subagents edit business code, while the controller delegates, reviews evidence, resolves conflicts, verifies, and reports. Use controller-implementation only when the user explicitly asks the controller to edit code itself.
- Write handoffs when context gets long, work pauses, rules change, decisions are withdrawn, or agents are replaced.
- Required tool usage must be proven before acceptance.

### Orchestration primitives

The skill's orchestration actions map to these Claude Code capabilities:

| Orchestration action | Claude Code |
|---|---|
| Spawn a subagent | `Agent` tool, picking a `subagent_type` per task |
| Reuse a subagent | `SendMessage`, continuing that agent by name or ID with its context intact |
| Wait and monitor | Completion notifications, with `TaskList` / `TaskOutput` |
| Write isolation | `isolation: "worktree"` |
| Lifecycle wind-down | Subagents terminate after returning a final report; move the ledger entry to a terminal status |

Note that a subagent's final report is not shown to the user directly, so the controller must relay what matters.

### When to use it

Do not make `subagent-orchestration` the default entry point for every task; forcing it onto small tasks adds coordination overhead.

```text
Does the task need multiple executors, multiple artifacts, cross-context continuation, independent acceptance, or multi-evidence test regression?
Yes -> subagent-orchestration
No  -> just do the work, or use the relevant domain skill
```

Recommended startup prompt:

```text
If the current role is architect/reviewer/controller, stay in review-only or
plan-handoff mode until explicit implementation authorization is given.
After authorization, default to delegated-implementation: subagents write
business code and the controller verifies instead of editing directly.
```

Pair this skill with domain skills; keep domain-specific rules in the relevant domain skill.
