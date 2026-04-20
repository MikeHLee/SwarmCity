---
title: Multi-Agent Workflow
nav_order: 4
---

# Multi-Agent Workflow

This guide walks through the complete flow for running a multi-agent team with
dot_swarm: spawning workers and role agents in tmux, enforcing proof-of-work via
the inspector role, and merging completed items back to main.

---

## Prerequisites

```bash
pip install dot-swarm
brew install tmux              # tmux 3.0+ required for swarm spawn
```

Plus one or more agent CLIs on your PATH:

| Agent | Install |
|-------|---------|
| opencode | [opencode.ai](https://opencode.ai) |
| claude | [claude.ai/code](https://claude.ai/code) |
| ollama | [ollama.com](https://ollama.com) — then `ollama pull llama3.2` |
| bedrock | `pip install 'dot-swarm[ai]'` + AWS credentials |

---

## Step 1: Initialise the swarm

```bash
cd your-repo
swarm init                    # creates .swarm/, generates signing identity
swarm crawl                   # populate context.md with directory structure
swarm add "Implement OAuth2 login" --priority high
swarm add "Add rate limiting to API" --depends AUTH-001
swarm ready                   # confirm AUTH-001 is unblocked, AUTH-002 is not
```

---

## Step 2: Enable the inspector role

The inspector role adds a proof-of-work gate — workers can't call `swarm done`
until they've attached evidence and an inspector has verified it.

```bash
swarm role enable inspector \
  --max-iterations 3 \
  --require-proof "branch,commit,tests"
```

| Option | Meaning |
|--------|---------|
| `--max-iterations 3` | Auto-BLOCK item after 3 consecutive failures |
| `--require-proof "branch,commit,tests"` | Worker must supply all three fields |

---

## Step 3: Spawn a worker

`swarm spawn` opens a named tmux window, sets the `SWARM_*` environment variables,
and auto-claims the item.

```bash
swarm spawn AUTH-001 --agent opencode
```

What happens under the hood:

1. A tmux session named `swarm` is created (or reused)
2. A window named `AUTH-001` is opened with `opencode` running inside it
3. Three env vars are set before opencode starts:

| Variable | Value |
|----------|-------|
| `SWARM_AGENT_ID` | e.g. `spawn-AUTH-001-143022` |
| `SWARM_ITEM_ID` | `AUTH-001` |
| `SWARM_ROLE` | `worker` |

4. The item is claimed: `AUTH-001` moves from Pending → Active in `queue.md`

**Attach to the worker window:**
```bash
tmux attach -t swarm              # attach to session
# Ctrl-b + n                      # cycle windows
# Ctrl-b + s                      # session picker
```

**Worker options:**
```bash
swarm spawn AUTH-001 --agent claude      # use Claude Code instead
swarm spawn AUTH-001 --agent ollama      # use local Ollama model
swarm spawn AUTH-001 --no-claim          # open window without claiming
swarm spawn AUTH-001 --session oauth     # custom tmux session name
```

---

## Step 4: Worker does the work

Inside the worker's tmux window, the agent reads `BOOTSTRAP.md` and `context.md`
automatically (if using opencode or Claude Code with MCP configured). It works the
task, runs tests, pushes a branch.

When finished, the worker attaches proof instead of calling `swarm done`:

```bash
swarm partial AUTH-001 \
  --proof "branch:feature/oauth2 commit:abc1234 tests:42/42 pr:47"
```

The `proof:` field is stored inline in `queue.md` and validated against the
`require-proof` fields set during `swarm role enable`. Missing required fields
produce a warning but don't block the command.

**Common proof fields:**

| Field | Example |
|-------|---------|
| `branch` | `branch:feature/oauth2` |
| `commit` | `commit:abc1234` |
| `tests` | `tests:42/42` |
| `pr` | `pr:47` |
| `diff` | `diff:+187/-23` |

---

## Step 5: Spawn an inspector

```bash
swarm spawn --role inspector
```

This opens a second tmux window named `inspector` with `SWARM_ROLE=inspector`.
The inspector agent (or a human) reviews the proof and approves or rejects:

```bash
# Approve — item moves to Done, signed in trail.log
swarm inspect AUTH-001 --pass
swarm inspect AUTH-001 --pass --note "Tests green, code reviewed, PR #47 approved"

# Reject — item returns to Open, proof cleared, inspect_fails incremented
swarm inspect AUTH-001 --fail --reason "Token refresh edge case not handled — see test_auth.py:142"
```

**On `--fail`:** the item is re-opened, proof is cleared, and `inspect_fails` is
incremented. The worker sees it in `swarm ready` again and can re-claim it.

**On exhaust:** if `inspect_fails` reaches `max-iterations`, the item is
auto-BLOCKed with a clear message:

```
Max retries exhausted: [AUTH-001] is now BLOCKED (3/3 fails).
  Use 'swarm unblock --reclaim' to manually reassign, or 'swarm done --force' to override.
```

Blocked items surface immediately in `swarm audit --full` and `swarm status`.

---

## Step 6: Supervisor overview (optional)

A supervisor window gives a human director or orchestrator agent a live view
across all active work:

```bash
swarm spawn --role supervisor
```

Inside the supervisor window:
```bash
swarm explore --depth 3          # colony heartbeat
swarm report --only active       # active items only
swarm audit --full               # full health + security pass
swarm ready                      # what's unblocked right now
```

---

## Step 7: Merge

Once `swarm inspect AUTH-001 --pass` has run, `AUTH-001` is Done and the branch
is ready to merge. In the worker's window (or a dedicated merge window):

```bash
gh pr merge 47 --squash --delete-branch
```

Then continue: `swarm ready` surfaces `AUTH-002` (rate limiting), which was
blocked on `AUTH-001`. Spawn a worker for it and repeat.

---

## Human override

```bash
swarm done AUTH-001 --force      # skip inspector gate entirely (human director only)
swarm unblock AUTH-001 --reclaim # re-open a BLOCKED item for a fresh worker
```

---

## Full example session

```bash
# ── Terminal 1: setup ────────────────────────────────────────────────
swarm init --crawl
swarm role enable inspector --max-iterations 3 --require-proof "branch,commit,tests"
swarm add "Implement OAuth2 login" --priority high
swarm add "Add rate limiting" --depends AUTH-001

# ── Spawn workers ────────────────────────────────────────────────────
swarm spawn AUTH-001 --agent opencode      # worker window: AUTH-001
swarm spawn --role inspector               # inspector window
swarm spawn --role supervisor              # supervisor window

# ── Inside AUTH-001 worker window (opencode) ─────────────────────────
# ... implement, test, push branch ...
swarm partial AUTH-001 --proof "branch:feature/oauth2 commit:abc1234 tests:42/42 pr:47"

# ── Inside inspector window ──────────────────────────────────────────
swarm inspect AUTH-001 --pass --note "All good, merging"

# ── Back in Terminal 1 ───────────────────────────────────────────────
gh pr merge 47 --squash --delete-branch
swarm ready         # AUTH-002 now unblocked
swarm spawn AUTH-002 --agent opencode
```

---

## Environment variables reference

These are set automatically by `swarm spawn` in each tmux window:

| Variable | Set by | Description |
|----------|--------|-------------|
| `SWARM_AGENT_ID` | `swarm spawn` | Unique agent identifier for this window |
| `SWARM_ITEM_ID` | `swarm spawn <id>` | The item being worked |
| `SWARM_ROLE` | `swarm spawn --role` | `worker`, `inspector`, `supervisor`, or `watchdog` |

Any `swarm` command that accepts `--agent` will default to `$SWARM_AGENT_ID` if set.

---

## Which AI backend to use?

| Backend | Best for | Setup |
|---------|----------|-------|
| `opencode` | Full agentic coding (reads files, runs tests) | `npm i -g opencode` |
| `claude` | Claude Code interactive sessions | `npm i -g @anthropic-ai/claude-code` |
| `ollama` | Local/private models, no API keys | `brew install ollama && ollama pull llama3.2` |
| `bedrock` | AWS-native teams | `pip install 'dot-swarm[ai]'` + AWS creds |

Configure the default with `swarm configure`, or override per-command with `--via`:

```bash
swarm ai "what should I work on?" --via ollama
swarm ai "mark AUTH-001 done" --via bedrock
```
