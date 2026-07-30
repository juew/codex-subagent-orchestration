# Subagent Orchestration

中文 | [English](#english)

## 中文

`subagent-orchestration` 是一个通用 Claude Code skill，用于主控 + 子 agent 工作模式。它适合长流程、多 agent、需要验收门槛、工具使用证明、上下文交接和最终一致性检查的任务。

这个发布包只包含一个独立 skill：

- `subagent-orchestration`

## 适用场景

- 主控负责规划、分派、验收和最终一致性。
- 子 agent 只执行边界清晰的任务。
- 需要把工具使用证明作为验收门槛。
- 上下文变长、任务暂停或 agent 换班时，需要交接文档。
- 需要并行推进但又不能丢失状态或责任边界。
- 服务器页面回归、业务流程测试、验收测试等需要覆盖矩阵、截图、日志、JSON 证据、`PASS/FAIL/BLOCKED` 报告，且主控需要验收多个证据来源。

## 何时启用

`subagent-orchestration` 是执行层，不是入口层。先按 Claude Code 正常的 skill 发现规则判断任务类型，只有当任务已经被判断为长流程、多 agent、需要 handoff 或需要独立验收时，才启用它。

简单判断：

```text
是否需要多个执行者、多个产物、跨上下文延续、独立验收、或多证据测试回归？
是 -> subagent-orchestration
否 -> 直接做，或使用对应的领域 skill
```

不要让 `subagent-orchestration` 成为所有任务的默认入口。它更像项目经理模式，适合复杂任务；小任务强行启用会增加文书和协调成本。

## 编排原语

| 编排动作 | Claude Code |
|---|---|
| 派生子 agent | `Agent` 工具，按任务选择 `subagent_type` |
| 复用子 agent | `SendMessage`，按 agent 名称或 ID 延续其上下文 |
| 等待与监控 | 后台完成通知，配合 `TaskList` / `TaskOutput` |
| 写边界隔离 | `isolation: "worktree"` |
| 生命周期收尾 | 子 agent 返回最终报告后自行终止，总账置终态即可 |

## 安装

复制本仓库中的 skill 到你的 Claude Code skills 目录：

```bash
cp -R skills/subagent-orchestration ~/.claude/skills/
```

重启 Claude Code 后，用 `/subagent-orchestration` 调用，或由 Claude 在任务匹配时自动加载。

仓库根目录带有 `.claude-plugin/plugin.json`，因此也可以作为 Claude Code 插件分发。

## English

`subagent-orchestration` is a general Claude Code skill for main-controller + subagent workflows. It is designed for long-running work that needs delegation, acceptance gates, proof of required tool usage, context handoffs, and final consistency checks.

This release package contains one independent skill:

- `subagent-orchestration`

## Use Cases

- The main controller owns planning, delegation, acceptance, and final consistency.
- Subagents execute tightly scoped tasks.
- Required tool usage must be proven before acceptance.
- Handoff documents are needed when context grows, work pauses, or agents are replaced.
- Parallel work must remain coordinated without losing state or responsibility boundaries.
- Server/page regression, business-flow testing, and acceptance testing need coverage matrices, screenshots, logs, JSON evidence, `PASS/FAIL/BLOCKED` reports, or controller acceptance across multiple evidence sources.

## When To Use It

`subagent-orchestration` is an execution layer, not an entry point. Let Claude Code's normal skill-discovery rules classify the task first, and invoke this skill only once the work is classified as long-running, multi-agent, handoff-sensitive, or requiring independent acceptance.

Use this quick decision rule:

```text
Does the task need multiple executors, multiple artifacts, cross-context continuation, independent acceptance, or multi-evidence test regression?
Yes -> subagent-orchestration
No  -> just do the work, or use the relevant domain skill
```

Do not make `subagent-orchestration` the default entry point for every task. It is a project-manager mode for complex work; forcing it onto small tasks adds coordination overhead.

## Orchestration Primitives

| Orchestration action | Claude Code |
|---|---|
| Spawn a subagent | `Agent` tool, picking a `subagent_type` per task |
| Reuse a subagent | `SendMessage`, continuing that agent by name or ID with its context intact |
| Wait and monitor | Completion notifications, with `TaskList` / `TaskOutput` |
| Write isolation | `isolation: "worktree"` |
| Lifecycle wind-down | Subagents terminate after returning a final report; move the ledger entry to a terminal status |

## Installation

Copy the skill into your Claude Code skills directory:

```bash
cp -R skills/subagent-orchestration ~/.claude/skills/
```

Restart Claude Code, then invoke it with `/subagent-orchestration`, or let Claude load it automatically when the task matches.

The repository root ships a `.claude-plugin/plugin.json`, so it can also be distributed as a Claude Code plugin.
