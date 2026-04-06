# CLI Reference

`swarm` is installed as a standalone command via `pip install dot-swarm`.

```bash
pip install dot-swarm           # base CLI
pip install 'dot-swarm[ai]'     # + AWS Bedrock support (boto3)
```

---

## Global Options

| Flag | Default | Description |
|------|---------|-------------|
| `--path PATH` | `.` (cwd) | Root path to search for `.swarm/` directory |
| `--version` | — | Print version and exit |
| `--help` | — | Show help |

All commands inherit `--path`. Example: `swarm --path ../oasis-cloud status`

---

## Initialization

### `swarm init`

Initialize a `.swarm/` directory in the current repo.

```bash
swarm init                   # auto-detect org vs division level
swarm init --level org       # force org level (ORG- item IDs)
swarm init --level division  # force division level
swarm init --code CLD        # set division code (default: derived from folder name)
```

Creates: `BOOTSTRAP.md`, `context.md`, `state.md`, `queue.md`, `memory.md`

---

## Situational Awareness

### `swarm status`

Print current state and active/pending queue items for this division.

```bash
swarm status          # active + pending items only
swarm status --all    # include done items
```

### `swarm ls`

List queue items with filtering.

```bash
swarm ls                            # all items
swarm ls --section active           # active only
swarm ls --section pending          # pending only
swarm ls --priority high            # filter by priority
swarm ls --project cloud-stability  # filter by project tag
```

### `swarm explore`

Show the heartbeat of all divisions in the colony. Recursively discovers `.swarm/` directories.

```bash
swarm explore                       # from current directory, depth 2
swarm explore --depth 3             # search deeper
swarm --path ~/org explore          # from org root
```

### `swarm report`

Generate a full markdown report of all divisions. Unlike `explore`, outputs a complete
document suitable for sharing, filing as a GitHub issue, or posting to a wiki.

```bash
swarm report                        # print to stdout
swarm report --out REPORT.md        # write to file
swarm report --only active          # active items only
swarm report --no-done              # skip done sections
```

---

## Work Item Lifecycle

### `swarm add`

Add a new work item to the Pending queue.

```bash
swarm add "Add request ID tracing to all services"
swarm add "Fix Redis timeout" --priority high --project infra
swarm add "OAuth2 discovery" --notes "See RFC 8414 for discovery spec"
```

Options: `--priority [low|medium|high|critical]`, `--project TEXT`, `--notes TEXT`

### `swarm claim`

Claim an item (move Active, stamp with agent ID + timestamp).

```bash
swarm claim CLD-042
swarm claim CLD-042 --agent my-agent-id
```

### `swarm done`

Mark a claimed item as done.

```bash
swarm done CLD-042
swarm done CLD-042 --note "Used converse API instead of invoke-model"
```

### `swarm partial`

Checkpoint progress on a claimed item without marking it done. Updates the item's
in-progress note and refreshes the claim timestamp.

```bash
swarm partial CLD-042 "Auth header parsing done, token validation next"
```

### `swarm block`

Mark a claimed item as blocked.

```bash
swarm block CLD-042 "Waiting for staging DB credentials from ops"
```

### `swarm unblock`

Clear a blocked item back to Open (or back to Claimed if an agent is specified).

```bash
swarm unblock CLD-042                  # → OPEN
swarm unblock CLD-042 --reclaim        # → re-CLAIMED by current agent
```

---

## Memory & Audit

### `swarm audit`

Check for drift: stale claims, blocked items, pending items, security scan, and AI-powered code-vs-docs drift check.

```bash
swarm audit                  # Basic: stale claims + blocked items (always shown)
swarm audit --pending        # Also list all pending items
swarm audit --security       # Add adversarial content scan of .swarm/ files
swarm audit --drift          # Add AI code-vs-docs drift check (requires LLM backend)
swarm audit --trail          # Verify pheromone trail HMAC signatures
swarm audit --full           # All of the above
swarm audit --since 24       # Stale threshold in hours (default: 48)
```

**`--security`** scans `.swarm/` markdown files and platform shims (CLAUDE.md, .windsurfrules, .cursorrules) for:
- `CRITICAL`: Prompt injection, instruction erasure, persona hijacking, jailbreaks, LLM template injection
- `HIGH`: Non-disclosure directives, hidden instructions, control characters, priority manipulation
- `MEDIUM`: Hidden HTML/markdown comments, HTML injection, code injection

**`--drift`** runs the same AI analysis as the GitHub Actions drift-check workflow, locally. Compares the last 5 commits against `.swarm/` state to detect misalignment.

**`--trail`** re-verifies every HMAC-SHA256 signature in `trail.log`. Tampered entries are flagged with the agent fingerprint responsible.

### `swarm heal`

Full health pass: alignment + security scan + trail verification. Runs everything in sequence and logs all security findings to `memory.md` (findings are never silently swallowed).

```bash
swarm heal                   # Read-only health check
swarm heal --fix             # Quarantine adversarial content + block tampered trail signers
swarm heal --depth 2         # Descend two levels into child divisions (default: 1)
```

**Sections run by `swarm heal`:**
1. **Alignment** — ascend (local ↔ parent) + descend (local ↔ children). Identifies orphaned items with no cross-division links.
2. **Queue Health** — stale claims, blocked items, pending item count.
3. **Security Scan** — same 18-pattern scan as `swarm audit --security`, covering all `.swarm/` files and platform shims.
4. **Pheromone Trail Integrity** — HMAC-SHA256 re-verification of `trail.log`.
5. **Summary** — total issues, memory.md log entry, remediation hint if `--fix` not used.

**With `--fix`:**
- Copies flagged files to `.swarm/quarantine/<timestamp>_<file>.bak` for human forensic review. Does **not** auto-delete content — humans must excise injections.
- Blocks HMAC fingerprints of tampered trail entries in `.swarm/blocked_peers.json`.
- Run `swarm heal` again after cleaning to confirm resolution.

### `swarm handoff`

Print a structured handoff note for the current session — what was done, what's in
flight, what's next. Useful at the end of a work session.

```bash
swarm handoff
swarm handoff --format json    # machine-readable output
```

---

## Federation

OGP-lite cross-swarm federation — exchange work items and alignment signals between separate `.swarm/` hierarchies using signed intent messages. Trust is bilateral and explicit; there is no central registry.

**Key design principles (from OGP build learnings):**
- Identity is always derived from a stored key fingerprint, never from a path or claimed header field.
- Peer records are persisted *before* the trust operation returns (avoids the "addPeer lost on restart" bug).
- Every inbound message passes through a three-layer doorman before any queue operation is executed.

### `swarm federation init`

Create the `federation/` directory structure inside `.swarm/`.

```bash
swarm federation init
```

Creates: `federation/trusted_peers/`, `federation/inbox/`, `federation/outbox/`, `federation/policy.md`, `federation/exports.md`.

### `swarm federation export-id`

Print this swarm's public identity — the file to share with federation peers out-of-band (email, Slack, git).

```bash
swarm federation export-id              # print to stdout
swarm federation export-id --out id.json  # write to file
```

This is safe to commit or share. The private `.signing_key` is never exposed.

### `swarm federation trust`

Import a peer's identity file and establish bilateral trust.

```bash
swarm federation trust peer_identity.json
swarm federation trust peer_identity.json --name "Acme Corp" --scopes "work_request,alignment_signal"
```

| Option | Default | Description |
|--------|---------|-------------|
| `--name NAME` | peer's swarm ID | Human-readable label |
| `--scopes SCOPES` | `work_request,alignment_signal` | Comma-separated list of permitted intents |

### `swarm federation revoke`

Remove a peer from trusted peers.

```bash
swarm federation revoke <fingerprint>
```

### `swarm federation peers`

List all trusted federation peers and their permitted scopes.

```bash
swarm federation peers
```

### `swarm federation send`

Create a signed outbound intent message in `outbox/`. Deliver the resulting file to the peer manually (git push, shared directory, email attachment).

```bash
swarm federation send <fingerprint> work_request --desc "Need help with OAuth2 token exchange"
swarm federation send <fingerprint> alignment_signal --context "Completed auth module"
swarm federation send <fingerprint> capability_ad --context "Available for API integration work"
```

**Intent types:**

| Intent | Effect on peer | Notes |
|--------|---------------|-------|
| `work_request` | Adds item to peer's queue | Requires `work_request` scope |
| `alignment_signal` | Informational only | No queue change at peer |
| `capability_ad` | Informational only | Advertise what this swarm can do |

### `swarm federation inbox`

List received messages waiting in `inbox/`.

```bash
swarm federation inbox
```

### `swarm federation apply`

Apply a received inbox message to this swarm's queue after doorman enforcement.

```bash
swarm federation apply inbox/20260406T1400Z_work_request_ab123456.json
swarm federation apply inbox/msg.json --yes   # skip confirmation prompt
```

**Doorman enforcement sequence** (Layer 1 → 2 → 3):
1. Parse the message and read `from_fingerprint` from the message body (never the claimed header)
2. Layer 2: Is this fingerprint in `trusted_peers/`? Does their record permit this intent?
3. Layer 1: Does `federation/policy.md` allow this intent globally?

A `403`-equivalent reason is printed for any failure at any layer.

### Federation Policy

`federation/policy.md` is Layer 1 of the scope model. To disable an intent globally:

```markdown
disabled: work_request
```

Per-peer scopes in `trusted_peers/<fingerprint>.json` are Layer 2. Both must pass for a message to be applied.

### Upgrade Path

The current implementation exchanges identity files out-of-band and signs messages with HMAC-SHA256 for local trail integrity. The natural upgrade path to full OGP:

| Now (OGP-lite) | Full OGP |
|----------------|----------|
| Identity via `swarm federation export-id` (manual) | Ed25519 public key, discoverable via DNS `_ogp.example.com` TXT record |
| Transport: git push / shared dir / manual | HTTP/gRPC OGP gateway |
| HMAC-SHA256 local trail signing | Ed25519 asymmetric signatures (peers can verify independently) |
| `trusted_peers/` files | Bilateral gateway trust handshake |

---

## Scheduling

Schedules are stored in `.swarm/schedules.md`. No daemon required — intended to be called from the system crontab or triggered manually.

### `swarm schedule list`

```bash
swarm schedule list
```

### `swarm schedule add`

```bash
swarm schedule add '0 */6 * * *' 'swarm heal --fix'             # every 6 hours
swarm schedule add '6h' 'swarm audit --security' --name 'Security check'
swarm schedule add 'on:done CLD-042' 'swarm ai "claim CLD-043"'  # event-driven
```

**Schedule types:**

| Type | Spec format | Example |
|------|------------|---------|
| `cron` | 5-field cron | `0 9 * * 1` (Mondays 9am) |
| `interval` | `Nm` / `Nh` / `Nd` | `30m`, `6h`, `2d` |
| `on:done` | `on:done ITEM-ID` | `on:done CLD-042` |
| `on:blocked` | `on:blocked ITEM-ID` | `on:blocked CLD-042` |

### `swarm schedule remove`

```bash
swarm schedule remove SCHED-001
```

### `swarm schedule run`

Manually trigger a specific schedule regardless of due status.

```bash
swarm schedule run SCHED-001
```

### `swarm schedule run-due`

Run all currently-due cron/interval schedules. Add to system crontab:

```bash
# In crontab (crontab -e):
* * * * *  cd /path/to/repo && swarm schedule run-due

# Or manually:
swarm schedule run-due
```

---

## Workflows

Workflows are markdown files in `.swarm/workflows/*.md` with a YAML frontmatter header. They define multi-step sequences of `swarm` commands or arbitrary shell commands.

**Patterns** (inspired by swarms.ai):
- **`sequential`** — steps run in order; halts on first failure
- **`concurrent`** — all steps run in parallel threads
- **`conditional`** — steps have `if:` guards based on previous step results
- **`mixture`** — concurrent with result aggregation (implement per-step `agent:` assignments)

### `swarm workflow create`

Scaffold a new workflow file.

```bash
swarm workflow create oauth2-flow --pattern sequential --trigger "on:done CLD-041"
swarm workflow create weekly-report --pattern sequential --trigger "0 9 * * 1"
```

Edit the generated `.swarm/workflows/<name>.md`:

```markdown
---
trigger: on:done CLD-041
pattern: sequential
description: OAuth2 integration sequence
---

## Steps

1. swarm claim CLD-042
   agent: bedrock
   timeout: 30

2. swarm claim CLD-043
   agent: claude
   depends: CLD-042
   timeout: 45
   if: step1.ok

3. swarm heal --fix
   agent: auto
   timeout: 5
```

### `swarm workflow list`

```bash
swarm workflow list
```

### `swarm workflow show`

```bash
swarm workflow show oauth2-flow
```

### `swarm workflow run`

```bash
swarm workflow run oauth2-flow              # confirm before running
swarm workflow run oauth2-flow --dry-run    # show steps, no execution
swarm workflow run oauth2-flow --yes        # skip confirmation
```

### `swarm workflow status`

Show last run result from `.swarm/workflow_runs.jsonl`.

```bash
swarm workflow status oauth2-flow
```

---

## AI Interface

### `swarm ai`

Translate a natural-language instruction into `.swarm/` operations using an LLM backend.
Previews proposed changes before executing (unless `--yes`).

```bash
swarm ai "mark CLD-042 as done, merged the OAuth PR"
swarm ai "what should I work on next?"
swarm ai "add three items for rate limiting: design, implement, test"
swarm ai "write a memory entry: chose NATS over Kafka for lower latency"
swarm ai "update focus to markets ASGI fix" --yes

# With a specific backend:
swarm ai "summarise the queue" --via claude
swarm ai "what needs doing?" --via gemini
swarm ai "mark done" --via bedrock      # explicit Bedrock (default)
```

Options: `--yes / -y`, `--agent TEXT`, `--limit INT` (context token budget), `--via [bedrock|claude|gemini|opencode]`, `--chain`, `--max-steps INT`

**Workflow chaining (`--chain`)**:

With `--chain`, the AI is re-invoked after each successful set of write operations using the refreshed `.swarm/` context. This continues until the AI returns no further write ops (work is complete) or `--max-steps` is reached.

Each batch of chained operations is signed and recorded in `trail.log`.

```bash
swarm ai "run the OAuth2 workflow: discovery, token exchange, refresh" --chain --yes
swarm ai "implement auth, then markets, then geo modules" --chain --max-steps 9 --yes
swarm ai "process the full pending queue" --chain --max-steps 20 --yes
```

Use `--yes` with `--chain` for fully automated runs; omit it to confirm each step interactively.

### `swarm session`

Launch an interactive LLM session in the division root, seeded with `.swarm/` context.

```bash
swarm session                          # interactive, auto-detect CLI
swarm session --with claude            # prefer Claude Code
swarm session --with gemini            # prefer Gemini CLI
swarm session "what should I pick up?" # single non-interactive turn
```

For **Claude Code**: CLAUDE.md already loads `.swarm/` context automatically.
For **gemini / opencode**: writes `.swarm/CURRENT_SESSION.md` context file first.

### `swarm configure`

Interactive wizard to set your default LLM interface and (if Bedrock) model + region.

```bash
swarm configure
```

Config stored at `~/.config/swarm/config.toml`. Credentials are never stored here —
use `aws configure` or env vars for Bedrock; the respective CLI handles auth for others.

---

## Setup & CI

### `swarm setup-drift-check`

Install the `swarm-drift-check.yml` GitHub Actions workflow into the current repo.
Uses the `gh` CLI to set secrets if needed.

```bash
swarm setup-drift-check           # install workflow file only
swarm setup-drift-check --commit  # also commit + push
```

See [Drift Check Setup](DRIFT_CHECK_SETUP.md) for AWS Bedrock prerequisites.

---

## Item ID Convention

```
<DIVISION-CODE>-<3-digit-number>
```

| Division | Code |
|----------|------|
| Org level | `ORG` |
| oasis-cloud | `CLD` |
| oasis-cloud-admin | `ADM` |
| oasis-weather | `WTH` |
| oasis-firmware | `FW` |
| oasis-home | `HM` |
| oasis-ui | `UI` |
| oasis-forms | `FRM` |
| oasis-hardware | `HW` |
| oasis-welcome | `WEB` |
| oasis-cloud-wiki | `WIKI` |
| oasis-records | `REC` |
| swarm-city | `SWC` |

IDs are assigned sequentially and never reused.

---

## Security & Trust Model

### Pheromone Trail Signing

Every `swarm init` generates a per-swarm HMAC-SHA256 signing identity:

| File | Description | Commit? |
|------|-------------|--------|
| `.swarm/identity.json` | Public fingerprint (swarm ID, algorithm, created) | ✅ Yes |
| `.swarm/.signing_key` | 256-bit private HMAC key | ❌ No (.gitignored) |
| `.swarm/trail.log` | Append-only signed operation log | ❌ No (local only) |
| `.swarm/blocked_peers.json` | Blocked fingerprints | ✅ Optional |

Each `swarm ai` batch records a signed entry in `trail.log`:
```json
{"timestamp":"2026-04-06T14:00Z","swarm_id":"a1b2c3d4","fingerprint":"f8e7d6c5","agent_id":"cascade","op":"ai_batch","payload":{"step":1,"ops":["done","write_state"]},"signature":"abc123..."}
```

To verify the trail: `swarm audit --trail` or `swarm heal`.
To block a bad actor: `swarm heal --fix` (auto-blocks tampered fingerprints).

### Adversarial Content Detection

`swarm heal` and `swarm audit --security` scan for 18 patterns across 3 severity levels:

| Severity | Categories |
|----------|------------|
| **CRITICAL** | PROMPT_INJECTION, INSTRUCTION_ERASURE, PERSONA_HIJACK, JAILBREAK, LLM_TEMPLATE_INJECTION, SAFETY_OVERRIDE |
| **HIGH** | NON_DISCLOSURE, CONTROL_CHARACTERS, PRIORITY_OVERRIDE |
| **MEDIUM** | HIDDEN_HTML_COMMENT, HIDDEN_MD_COMMENT, HTML_INJECTION, CODE_INJECTION |

Files scanned: `state.md`, `queue.md`, `memory.md`, `context.md`, `BOOTSTRAP.md`, `workflows/*.md`, `CLAUDE.md`, `.windsurfrules`, `.cursorrules`, `.github/copilot-instructions.md`.

### swarms.ai Integration

For multi-agent frameworks, use the built-in bridge:

```python
from dot_swarm.swarms_provider import DotSwarmStateProvider, StigmergicSwarm

# Inject .swarm/ state into any agent's system prompt
provider = DotSwarmStateProvider(swarm_path="./.swarm")
system_prompt = provider.build_system_prompt(agent_name="Coordinator")

# Read queue state
queue = provider.get_queue()   # {"active": [...], "pending": [...], "done": [...]}

# Apply AI response operations back to .swarm/ files
results = provider.apply_operations(llm_response_json, agent_id="my-agent")

# Stigmergic multi-agent coordination (requires: pip install swarms)
from swarms import Agent
swarm = StigmergicSwarm(swarm_path=".", agents=[agent1, agent2], max_rounds=10)
results = swarm.run("Implement the OAuth2 integration")
```

Agents coordinate *indirectly* through `.swarm/` files (stigmergic protocol) — no direct agent-to-agent message passing required. Full git audit trail maintained automatically.
