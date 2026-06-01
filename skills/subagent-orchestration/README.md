# Subagent Orchestration for Codex

中文 | [English](#english)

## 中文

`subagent-orchestration` 是一个通用 Codex skill，用于长流程、多子 agent 的任务编排。它帮助主控 agent 规划任务、分派边界清晰的子任务、设置验收门槛、管理上下文交接、监督工具使用，并在结束前检查所有正式产物的一致性。

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
- 上下文变长、任务暂停、规则变化、结论撤销或 agent 换班时必须写交接文档。
- 如果用户要求某个工具，工具使用证明必须成为验收门槛。

与 `using-superpowers` 配合时，先让 `using-superpowers` 判断当前任务应该使用哪些 skill；只有当任务被判断为长流程、多 agent、需要 handoff 或需要独立验收时，才启用 `subagent-orchestration`。

快速判断：

```text
是否需要多个执行者、多个产物、跨上下文延续、或独立验收？
是 -> subagent-orchestration
否 -> 只用 using-superpowers 找到对应领域 skill
```

推荐启动话术：

```text
请先按 using-superpowers 选择适用 skill。
如果任务被判断为长流程、多 agent、或需要 handoff，
再使用 subagent-orchestration 作为主控流程。
```

不要把 `subagent-orchestration` 作为所有任务的默认入口；小任务强行启用会增加文书和协调成本。

建议和领域 skill 配合使用；领域规则保留在对应领域 skill 中。

## English

`subagent-orchestration` is a general-purpose Codex skill for long-running work that uses a main controller and bounded subagents. It helps the controller plan work, delegate scoped tasks, enforce acceptance gates, manage context handoffs, supervise required tool usage, and verify final artifact consistency.

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
- Write handoffs when context gets long, work pauses, rules change, decisions are withdrawn, or agents are replaced.
- Required tool usage must be proven before acceptance.

When using this with `using-superpowers`, let `using-superpowers` decide which skills apply first. Invoke `subagent-orchestration` only when the task is classified as long-running, multi-agent, handoff-sensitive, or requiring independent acceptance.

Quick decision rule:

```text
Does the task need multiple executors, multiple artifacts, cross-context continuation, or independent acceptance?
Yes -> subagent-orchestration
No  -> use using-superpowers to select the relevant domain skill
```

Recommended startup prompt:

```text
First use using-superpowers to select the applicable skills.
If the task is classified as long-running, multi-agent, or requiring handoff,
then use subagent-orchestration as the controller workflow.
```

Do not make `subagent-orchestration` the default entry point for every task; forcing it onto small tasks adds coordination overhead.

Pair this skill with domain skills; keep domain-specific rules in the relevant domain skill.
