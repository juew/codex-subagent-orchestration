# Codex Subagent Orchestration

中文 | [English](#english)

## 中文

`subagent-orchestration` 是一个通用 Codex skill，用于主控 + 子 agent 工作模式。它适合长流程、多 agent、需要验收门槛、工具使用证明、上下文交接和最终一致性检查的任务。

这个发布包提供一个独立 skill 和可选的、无需安装到用户全局目录的本地 hook：

- `subagent-orchestration`

版本 `0.2.0` 的 hook 由 Codex 自动从 `hooks/hooks.json` 发现。它们只读取当前工作目录的
`<cwd>/.codex/subagent-orchestration/ledger.json`：没有该文件时三个 hook 都静默放行；有该文件时，
会检查带 `ORCHESTRATION_TASK_ID` 的 `spawn_agent` 结构化 skill 项、子 agent 的最终 JSON 报告，以及
已验收任务的依赖、工具、skill 和相对且非空的证据文件。ledger 和证据格式见
`skills/subagent-orchestration/references/hook-evidence-contract.md`。

## 适用场景

- 主控负责规划、分派、验收和最终一致性。
- 子 agent 只执行边界清晰的任务。
- 需要把工具使用证明作为验收门槛。
- 上下文变长、任务暂停或 agent 换班时，需要交接文档。
- 需要并行推进但又不能丢失状态或责任边界。
- 服务器页面回归、业务流程测试、验收测试等需要覆盖矩阵、截图、日志、JSON 证据、`PASS/FAIL/BLOCKED` 报告，且主控需要验收多个证据来源。

## 与 using-superpowers 配合使用

`using-superpowers` 是入口层，用来判断当前任务应该使用哪些 skill；`subagent-orchestration` 是执行层，只在任务已经被判断为长流程、多 agent、需要 handoff 或需要独立验收时启用。

简单判断：

```text
是否需要多个执行者、多个产物、跨上下文延续、独立验收、或多证据测试回归？
是 -> subagent-orchestration
否 -> 只用 using-superpowers 找到对应领域 skill
```

不要让 `subagent-orchestration` 成为所有任务的默认入口。它更像项目经理模式，适合复杂任务；小任务强行启用会增加文书和协调成本。

推荐启动话术：

```text
请先按 using-superpowers 选择适用 skill。
如果任务被判断为长流程、多 agent、或需要 handoff，
再使用 subagent-orchestration 作为主控流程。
```

`using-superpowers` 负责“该用什么方法”，`subagent-orchestration` 负责“复杂工作怎么被可靠地完成”。

## 安装

仅复制 `skills/subagent-orchestration` 到 skills 目录只会提供说明文本，不会启用 hook 的确定性验收。
需要确定性 enforcement 时，应通过已配置的 Codex marketplace 安装整个 plugin。安装后，在 Codex 中打开
`/hooks`，进入该 plugin 的 hook 配置，审阅 `hooks/hooks.json` 与 `scripts/verify_ledger.py`，并在此处信任/启用
这些 hook；只有启用后确定性 hook 才会运行。本仓库不修改任何用户全局 marketplace 或配置。

只需要编排说明时，可以复制 skill：

```bash
cp -R skills/subagent-orchestration ~/.codex/skills/
```

重启或刷新 Codex 后即可使用说明；hook enforcement 仍需要完整 plugin 安装。

## English

`subagent-orchestration` is a general Codex skill for main-controller + subagent workflows. It is designed for long-running work that needs delegation, acceptance gates, proof of required tool usage, context handoffs, and final consistency checks.

This release package contains one independent skill:

- `subagent-orchestration`

Version `0.2.0` also ships local command hooks, automatically discovered by Codex from
`hooks/hooks.json`. They read only `<cwd>/.codex/subagent-orchestration/ledger.json`: all three
hooks silently allow when it is absent; when present, they enforce structured skill items for
marked `spawn_agent` calls, final subagent JSON proof, and accepted-task dependencies, tool/skill
coverage, and relative non-empty evidence files. See
`skills/subagent-orchestration/references/hook-evidence-contract.md` for the executable contract.

## Use Cases

- The main controller owns planning, delegation, acceptance, and final consistency.
- Subagents execute tightly scoped tasks.
- Required tool usage must be proven before acceptance.
- Handoff documents are needed when context grows, work pauses, or agents are replaced.
- Parallel work must remain coordinated without losing state or responsibility boundaries.
- Server/page regression, business-flow testing, and acceptance testing need coverage matrices, screenshots, logs, JSON evidence, `PASS/FAIL/BLOCKED` reports, or controller acceptance across multiple evidence sources.

## Working with using-superpowers

`using-superpowers` is the entry layer that decides which skills apply to the current task. `subagent-orchestration` is the execution layer and should be invoked only after the work is classified as long-running, multi-agent, handoff-sensitive, or requiring independent acceptance.

Use this quick decision rule:

```text
Does the task need multiple executors, multiple artifacts, cross-context continuation, independent acceptance, or multi-evidence test regression?
Yes -> subagent-orchestration
No  -> use using-superpowers to select the relevant domain skill
```

Do not make `subagent-orchestration` the default entry point for every task. It is a project-manager mode for complex work; forcing it onto small tasks adds coordination overhead.

Recommended startup prompt:

```text
First use using-superpowers to select the applicable skills.
If the task is classified as long-running, multi-agent, or requiring handoff,
then use subagent-orchestration as the controller workflow.
```

`using-superpowers` decides which method to use; `subagent-orchestration` governs how complex work is completed reliably.

## Installation

Copying only `skills/subagent-orchestration` into a skills directory provides the instructions but
does not activate deterministic hook enforcement. For enforcement, install the entire plugin
through a configured Codex marketplace. After installation, open `/hooks` in Codex, open this
plugin's hook configuration, review `hooks/hooks.json` and `scripts/verify_ledger.py`, then trust
and enable the hooks there; deterministic hooks run only after that enablement. This repository
does not modify any user-global marketplace or config.

For instruction-only use, copy the skill:

```bash
cp -R skills/subagent-orchestration ~/.codex/skills/
```

Restart or refresh Codex to use the instructions; hook enforcement still requires full plugin
installation.
