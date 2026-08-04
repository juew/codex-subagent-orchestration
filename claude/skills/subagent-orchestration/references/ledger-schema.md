# Ledger Schema (v1)

Machine-checkable format for the state ledger required by the Main Workflow.

A free-form ledger cannot be verified by an automated or delegated check. Several
gates in this skill have no enforceable meaning without the fields defined here:
tool policy (Tool Policy Enforcement), evidence tiers (formal vs diagnostic),
dependency order (Acceptance Gates), and reuse accounting (Subagent Reuse).

## File Layout

One ledger per change. Archive the whole file when the change closes.

```
<artifact-root>/changes/<change-slug>/ledger.yaml
```

One ledger per change bounds its length to a single change's task count, so both
the controller's context cost and the evidence check's cost stay constant as a
project grows. Never append a new change to a closed ledger.

## Schema

```yaml
schema: v1
mode: delegated-testing        # Execution Boundary mode for this change:
                               # review-only | plan-handoff | delegated-testing
                               # | delegated-implementation
                               # | controller-implementation
root: .                        # Base for resolving every evidence path below.
                               # Repo root, an artifacts directory, or an
                               # absolute path. Does not assume a git repo.
change: checkout-regression-2026-08
objective: Verify the checkout flow across the three supported payment paths.
updated: 2026-08-05T14:20:00Z
failure_patterns:              # Optional. Stack-specific strings that indicate
  - "--- FAIL"                 # failure inside command/file evidence. Omit the
  - "panic:"                   # key entirely to disable that scan.
  - "AssertionError"

tasks:
  - id: T01                    # Assigned once, never reused, never renumbered.
    task: Card payment path completes and order appears in the orders table
    depends_on: []

    owner: ui-test-agent       # null while status is planned
    reuse: spawned new because no active agent held browser context
    tools_required: [mcp__Claude_Browser__computer, Bash]
    tools_proven:   [mcp__Claude_Browser__computer, Bash]

    status: accepted
    accepted_by: human         # human | controller | null
    accepted_at: 2026-08-05T11:05:00Z

    evidence:
      - kind: ui
        path: artifacts/T01/card-confirmation.png
        tier: formal
        tool: mcp__Claude_Browser__computer
        note: Order confirmation page showing order id and paid total
      - kind: command
        path: artifacts/T01/orders-query.log
        tool: Bash
        note: Query output showing the matching order row with status=paid

    check:
      run_by: null             # human-accepted tasks are not checked
      at: null
      result: null
      against: null

  - id: T02
    task: Wallet payment path completes and order appears in the orders table
    depends_on: [T01]
    owner: ui-test-agent
    reuse: reused ui-test-agent
    tools_required: [mcp__Claude_Browser__computer]
    tools_proven:   [mcp__Claude_Browser__computer]
    status: accepted
    accepted_by: controller
    accepted_at: 2026-08-05T13:40:00Z
    evidence:
      - kind: ui
        path: artifacts/T02/wallet-confirmation.png
        tier: formal
        tool: mcp__Claude_Browser__computer
        note: Confirmation page for the wallet path, order id visible
      - kind: external
        path: null
        tool: Bash
        note: Observed the orders row directly in the DB console; not captured
    check:
      run_by: evidence-checker
      at: 2026-08-05T13:41:00Z
      result: OK
      against: v1

  - id: T03
    task: Expired-card path shows the retry prompt and creates no order
    depends_on: [T01]
    owner: null
    reuse: null
    tools_required: [mcp__Claude_Browser__computer]
    tools_proven: []
    status: planned
    accepted_by: null
    accepted_at: null
    evidence: []
    check: { run_by: null, at: null, result: null, against: null }

  - id: T04
    task: Refund path returns funds and flips order status
    depends_on: [T02]
    owner: ui-test-agent
    reuse: reused ui-test-agent
    tools_required: [mcp__Claude_Browser__computer]
    tools_proven: []
    status: blocked
    accepted_by: null
    accepted_at: null
    evidence:
      - kind: ui
        path: artifacts/T04/refund-403.png
        tier: diagnostic
        tool: mcp__Claude_Browser__computer
        note: Refund action returns 403 for the test account
    check: { run_by: null, at: null, result: null, against: null }
    handoff: |
      Objective: verify the refund path end to end.
      Done: reached the refund action; reproduced a 403 on the test account.
      Blocked: the test account lacks the refund permission. Not a product bug.
      Options: (a) request the permission for the test account,
               (b) run this slice against staging with an admin account.
      Needs a decision before continuing. Also blocks any refund-dependent task.
      Forbidden: do not grant permissions directly on the shared environment.
```

## Field Authority

| Field | Written by | Constraint |
|---|---|---|
| `mode` | controller | One of the five Execution Boundary modes. Declared per change, not per task. |
| `root` | controller | Every `evidence[].path` resolves against this. Absolute paths inside `evidence[].path` are invalid. |
| `failure_patterns` | controller | Optional. Stack-specific. Omit to disable the failure scan. |
| `id` | controller | Assigned once. Deleting a task means marking it `superseded`; ids are never recycled or renumbered. |
| `task` | controller | A verifiable **outcome**, not an activity. "Order appears in the orders table", not "test the checkout". |
| `depends_on` | controller | Marking a task accepted while an upstream task is not accepted is out-of-order acceptance. |
| `owner` | controller | `null` until the task is assigned. |
| `reuse` | controller | Required for any assigned task. `reused <name>` or `spawned new because <reason>`. |
| `tools_required` | controller | Declared when delegating. |
| `tools_proven` | controller | Filled from what the subagent reports actually performed the key action. |
| `status` | controller | See state machine below. |
| `accepted_by` | controller | The controller may only write `controller`. `human` requires the user to have explicitly confirmed inspection; the controller then records it with a timestamp. |
| `accepted_at` | controller | Required when `status: accepted`. |
| `evidence` | controller | Populated from what the subagent returned. |
| `check` | the checker | The controller must not write `check.result`. |
| `handoff` | controller or subagent | Required for `blocked`, `failed`, `superseded`. |

## State Machine

```
planned ──assign──> active ──subagent delivers──> ready ──verified──> accepted
                      ^                             │
                      └──────── sent back ──────────┘

active | ready ──stuck──> blocked                    (handoff required)
any state ──> failed | superseded                    (handoff required)

active | ready ──no completion notification──> notification-pending
notification-pending ──evidence sufficient──> evidence-accepted-without-notification
```

`active` must not go straight to `accepted`. The `ready` step is what separates
delivery from acceptance; skipping it means the controller both delivered and
accepted the work. This is the structural form of the rule that
`READY_FOR_ACCEPTANCE` means "inspect my evidence", not "this is done".

## Evidence Kinds

| `kind` | Meaning | `path` | `tier` | Verification strength |
|---|---|---|---|---|
| `file` | Source, test, document, report | required | — | Strong: path is checkable, content readable |
| `command` | Command or test output written to disk | required | — | Strong: same, plus failure scanning |
| `ui` | Screenshot or recording | required | **required** | `formal` counts; `diagnostic` does not stand alone |
| `external` | An observation that was not captured to a file | `null` | — | **Weak: must record `tool`, cannot be the only evidence** |

`external` exists because some observations genuinely are not captured — a DB row
seen in a console, an API response observed once. Labeling it honestly is better
than letting it pass as a conclusion. A task whose evidence is entirely
`external`, or entirely `ui` at `diagnostic` tier, is not acceptably evidenced.

`note` states **what this evidence proves**, not what the file is.
"Confirmation page showing order id and paid total" — not "a screenshot".

## Check Record

`check` holds the result of the independent evidence check, written by the
checker and not by the controller.

```yaml
    check:
      run_by: <checker agent name | null>
      at: <ISO8601 | null>
      result: OK | WARN | BLOCK | null
      against: <evidence-check.md version | null>
```

Two properties matter:

- **Idempotent.** A non-null `result` freezes the task: the check does not run
  again. Verification catches false acceptance at the moment of acceptance;
  re-verifying an unchanged task on every turn costs linearly more as the ledger
  grows and always reaches the same conclusion.
- **Versioned.** `against` records which version of the check rubric passed this
  task. When the rubric tightens, existing records remain interpretable and only
  tasks that need re-checking are re-checked.

Because `check` is a fixed-size field that is overwritten rather than appended,
it does not grow with time. Ledger size is bounded by the change's task count.

## Measuring Whether the Check Actually Ran

`check.run_by` is written by the controller's own workflow, so it is
self-reported. It is still worth recording, because omission is a reliable
signal — skipping the check and skipping the record are the same failure — but a
non-null value alone does not prove the check ran.

On Claude Code, the objective record is the session transcript at
`~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl`, where every tool call is
written by the harness as `"type":"tool_use","name":"Agent"` with its input
inline. Comparing the ledger's `check` records against the transcript's actual
`Agent` calls measures the gap between what the controller reports and what
happened. That gap, not the raw skip rate, is what indicates whether
delegation-based verification is sufficient or whether harness-triggered
enforcement is needed.

When computing a rate, the denominator is tasks that reached `accepted` with
`accepted_by: controller`. Exclude `human`-accepted tasks, `superseded` and
`failed` tasks, and tasks still in `ready` or `active`.
