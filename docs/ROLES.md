# Agent Roles

Agent roles extend dot_swarm coordination with structured behaviors for multi-agent
task mode. Every role is **opt-in** — enabling one never affects queue.md or any
work items until that role's commands are explicitly invoked. Roles are stored as
JSON configs in `.swarm/roles/<name>.json` and can be toggled at any time.

```bash
swarm role list                        # see all roles + status
swarm role enable inspector            # turn on
swarm role disable inspector           # turn off (removes config file)
swarm role show inspector              # full config
```

---

## Available Roles

| Role | Purpose | Key command |
|------|---------|-------------|
| **inspector** | Requires proof-of-work before an item can be marked done | `swarm inspect` |
| **watchdog** | Escalates stuck items to humans after inspector loops fail | automatic |
| **supervisor** | Holistic progress view across all active items and phases | `swarm supervisor` *(roadmap)* |
| **librarian** | Catalogs directory contents into `.swarm/` context and queue | `swarm librarian` *(roadmap)* |

---

## Inspector

The inspector role solves the **"fake done" problem** — an LLM worker marking an item
complete without actually finishing the work. When enabled, workers cannot call
`swarm done` directly. Instead they must attach proof of work and let a designated
inspector agent verify it.

### Enabling

```bash
swarm role enable inspector
swarm role enable inspector --max-iterations 3 --require-proof "branch,commit,tests"
swarm role enable inspector --agent inspector-bot-1
```

| Option | Default | Description |
|--------|---------|-------------|
| `--max-iterations` | `3` | Fail count before watchdog escalation |
| `--require-proof` | `branch,commit` | Comma-separated required proof fields |
| `--agent` | *(any)* | Assign a specific agent ID as inspector |

### Worker flow

```bash
# 1. Claim and do the work normally
swarm claim CLD-042

# 2. Instead of swarm done, mark partial and attach proof
swarm partial CLD-042 --proof "branch:feature/oauth2 commit:abc1234 tests:42/42"
#   ^ dot_swarm validates that all required proof fields are present and warns if not
```

The `proof:` field accepts a space-separated list of `key:value` pairs. Required fields
are checked against `require_proof_fields` in the role config. Common fields:

| Field | Example |
|-------|---------|
| `branch` | `branch:feature/oauth2` |
| `commit` | `commit:abc1234` |
| `tests` | `tests:42/42` |
| `diff` | `diff:+187/-23` |
| `pr` | `pr:47` |

### Inspector flow

```bash
# Inspector agent (or human) reviews the proof, then passes or fails

swarm inspect CLD-042 --pass
swarm inspect CLD-042 --pass --note "Tests pass, code reviewed, merging"

swarm inspect CLD-042 --fail --reason "Edge case X not handled — see test_auth.py:142"
```

**On `--pass`:** the item is marked Done, the inspector's agent ID is recorded in
the trail, and the operation is signed in `trail.log`.

**On `--fail`:** the item is re-opened to `OPEN` state, `proof:` is cleared,
`inspect_fails` is incremented, and a failure note is appended. The worker will see
the item in `swarm ready` again and can re-claim it.

### Iteration limit and escalation

After `max_iterations` consecutive failures:

- If the **watchdog** role is also enabled: a watchdog alert is printed and the item
  is flagged for human review.
- If watchdog is **not** enabled: a plain warning is shown with the command to enable it.

```
Watchdog alert: CLD-042 has failed inspection 3/3 times. Human review required.
```

### Bypassing (human override)

```bash
swarm done CLD-042 --force    # skip inspector gate; for human directors only
```

### How the proof is stored

The `proof:` and `inspect_fails:` fields are stored inline in `queue.md`, just like
`priority:` and `notes:` — fully human-readable and git-diffable:

```markdown
- [>] [CLD-042] [CLAIMED · worker-1 · 2026-04-18T10:00Z · PARTIAL] Implement OAuth2
      priority: high | project: auth
      proof: branch:feature/oauth2 commit:abc1234 tests:42/42
      inspect_fails: 1
```

---

## Watchdog

The watchdog monitors for items that are stuck in an inspector loop or need domain
context that neither the worker nor inspector can resolve after multiple iterations.

When enabled alongside inspector, it automatically fires when `inspect_fails >=
max_iterations` on any item. It surfaces a human-readable escalation alert in the CLI
and (roadmap) can write to `.swarm/escalations.md` for async review.

```bash
swarm role enable watchdog
```

**Roadmap additions:**
- `.swarm/escalations.md` — append-only log of all escalated items
- `swarm watchdog report` — list all currently escalated items
- Optional webhook (Slack / GitHub Issues) on escalation

---

## Supervisor

The supervisor maintains a holistic view across all active items, in-flight phases,
and agent assignments. It provides structured progress briefs for a human director
without that person needing to read every queue.md manually.

```bash
swarm role enable supervisor
```

**Roadmap additions:**
- `swarm supervisor report` — aggregate active items + phase progress across all levels
- `swarm supervisor brief --format md` — concise markdown summary for a human director
- Integrates with `swarm ascend / descend` to roll up across the org hierarchy

---

## Librarian

The librarian crawls the directory tree of a division and populates `.swarm/` with
any undocumented modules or files — creating `OPEN` queue items for undocumented
components and flagging conflicts to the watchdog.

```bash
swarm role enable librarian
```

**Roadmap additions:**
- `swarm librarian catalog` — walk the tree, append to `context.md`, create queue items
  for undocumented files
- `swarm librarian diff` — list files not referenced in any queue item
- Conflicts (file exists but contradicts existing queue item) raised to watchdog if enabled

---

## Role Interaction Map

```
Worker agent
    │
    ├── swarm claim <id>
    ├── ... do work ...
    └── swarm partial <id> --proof "branch:X commit:Y tests:N/N"
                │
                ▼
        Inspector agent
            │
            ├── swarm inspect <id> --pass  ──► DONE (signed in trail.log)
            │
            └── swarm inspect <id> --fail  ──► re-OPEN (inspect_fails++)
                        │
                        │  (if inspect_fails >= max_iterations)
                        ▼
                Watchdog alert ──► human review
                        │
                        └── swarm done <id> --force  (human director override)
```

---

## Comparison with Gastown Roles

| dot_swarm | Gastown | Notes |
|-----------|---------|-------|
| inspector | Witness (partial) | dot_swarm inspector actively gates done; Witness monitors health |
| watchdog | — | No direct equivalent in Gastown |
| supervisor | Mayor (partial) | Mayor orchestrates work; supervisor observes and reports |
| librarian | — | No direct equivalent in Gastown |
| *(worker)* | Polecats | Ephemeral workers; in dot_swarm any agent with `$SWARM_AGENT_ID` |
| *(merge gate)* | Refinery | SWC-024 roadmap item |

dot_swarm roles are **advisory and toggleable** — you enable only what your workflow
needs. Gastown's roles are baked into the fixed colony architecture.
