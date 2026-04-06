# dot_swarm Integration Plan: Swarm Heal, OGP Federation, Scheduling & swarms.ai

**Created**: 2026-04-06
**Status**: PHASE 1 COMPLETE — implementation in progress
**Author**: Cascade + Mike Lee

---

## Decisions Made (2026-04-06)

| Decision | Choice | Rationale |
|---|---|---|
| Crypto signing | hashlib HMAC-SHA256 (stdlib) | No external deps; consistent with dot_swarm philosophy |
| Scheduler execution | cron (not daemon) | Unix-native; simpler process model |
| `.swarm` self-management | Yes | Use dot_swarm to track dot_swarm's own implementation |
| GitHub drift-check | Also available as `swarm audit --drift` (local) | Same-step parity between terminal and GHA workflow |
| swarms.ai PR scope | Start `DotSwarmStateProvider` → then `StigmergicSwarm` | Smaller contribution first, grow from there |
| Phase ordering | Complexity order (1→2→3→4) with blocker awareness | Crypto (Phase 1) unblocks Federation (Phase 3) |
| `swarm heal` security | Scan for injection, non-disclosure, persona-hijack; log to memory; quarantine on `--fix` | Findings must never be silently swallowed |
| `swarm ai --chain` | Auto-chain AI invocations; `--max-steps` guard; sign each batch in `trail.log` | Natural workflow composition through the AI interface |

## Phase Dependency Map

```
Phase 1a — signing.py + security.py + swarms_provider.py  ← DONE (SWC-010)
  │   [BLOCKS Phase 3: federation needs HMAC primitives]
  ▼
Phase 1b — swarm heal + swarm audit + swarm ai --chain     ← DONE (SWC-011)
  │   [heal used as workflow step in Phase 2]
  ▼
Phase 1c — docs/CLI_REFERENCE.md update                    ← DONE (SWC-012 complete)
  │   [users need docs before federation UX makes sense]
  ▼
Phase 2 — schedules.md + workflow composition (cron)       ← NEXT (SWC-013)
  │   [workflows needed for DotSwarmWorkflow adapter]
  │
  ├──▶ Phase 3 — OGP-lite federation                       ← After Phase 2 (SWC-014)
  │         [already unblocked: crypto done in Phase 1a]
  │
  └──▶ Phase 4b — StigmergicSwarm PR to swarms.ai          ← After Phase 2 (SWC-015)
             [DotSwarmStateProvider already done; needs workflows for full adapter]
```

---

## Executive Summary

This plan proposes four interconnected enhancements to dot_swarm, informed by research into Anthropic's persistent agent patterns, OGP federation, and the swarms.ai multi-agent framework. Each enhancement is designed to complement Oasis-X's existing cloud services (Sentinel, MQ, AI, Data) and the stigmergic coordination model that already underpins dot_swarm.

| # | Feature | Scope | Complexity |
|---|---------|-------|------------|
| 1 | `swarm heal` command | CLI + operations | Low |
| 2 | OGP-lite federation layer | Agent feature (new files) | Medium |
| 3 | Task scheduling & composition | Agent feature + MCP | Medium |
| 4 | swarms.ai integration (PR proposal) | External contribution | Medium |

---

## 1. `swarm heal` — Full Ascend + Descend Alignment Pass

### Motivation
The existing `ascend` and `descend` commands each check one direction of the division hierarchy. A "heal" pass runs both sequentially, producing a unified alignment report and optionally proposing corrective operations (add missing refs, flag orphaned items). This mirrors the "glymphatic" clearing concept from Anthropic's Kairos agent — a periodic full-system coherence check.

### What Exists Today
- `cli.ascend` — checks local→parent item references via `get_alignment()`
- `cli.descend` — checks local→children item references via `get_alignment()` + `discover_divisions()`
- `operations.get_alignment()` — finds cross-division `refs` / `depends` pairs
- `operations.audit()` — finds stale claims and blocked items

### Proposed Design

```
swarm heal [--fix] [--depth N]
```

**Behavior:**
1. Run `ascend` alignment check (local ↔ parent)
2. Run `descend` alignment check (local ↔ all children, depth N)
3. Run `audit` on local division
4. Cross-reference: find local items with no parent/child linkage ("orphans")
5. Find parent/child items that reference this division but have no local counterpart ("dangling refs")
6. Print a unified health report

**With `--fix`:**
- Auto-add missing `refs:` lines for items that should cross-reference
- Propose new queue items for dangling external references
- Update `state.md` with heal timestamp + summary

**Implementation files:**
- `src/dot_swarm/cli.py` — new `heal` command (~80 lines)
- `src/dot_swarm/operations.py` — new `heal_report()` function (~60 lines)
- No new dependencies

### Oasis-X Alignment
- Heal maps directly to the categorical ontology's consistency checking (commutative facts / obstruction detection in `CATEGORICAL_ONTOLOGY_ARCHITECTURE.md`)
- The Sentinel service's Trigger→Analysis→Reaction pattern is analogous: heal is an Analysis that detects misalignment, with optional Reactions (fix refs, add items)
- Could be scheduled via CI/CD drift check (already exists as `swarm setup-drift-check`)

---

## 2. OGP-Lite Federation Layer — IMPLEMENTED (SWC-014)

**Status**: Complete as of 2026-04-06. 34 tests passing.

### Motivation
OGP (Open Gateway Protocol, by David Proctor / Trilogy AI) defines the right semantics for cross-swarm federation: cryptographic identity, bilateral trust, signed intent messages, controlled boundaries. dot_swarm's git-native philosophy means we implement the *protocol semantics* without requiring a network gateway.

### OGP Build Learnings Applied

| OGP Lesson | Our Implementation |
|---|---|
| **Identity = key fingerprint, NOT hostname:port** | `trust_peer()` reads `fingerprint` from stored `identity.json`; addresses (paths) are treated as mutable |
| **Never trust the sender's claimed ID** | `doorman_check()` always looks up `from_fingerprint` from `trusted_peers/` — never trusts the message body's claim |
| **Persist before returning success** (addPeer bug) | `trust_peer()` calls `_atomic_write()` before `return peer` |
| **Three-layer scope model** | L1: `policy.md`, L2: `trusted_peers/<fp>.json` scopes, L3: `doorman_check()` at runtime |
| **HMAC-SHA256 is wrong for cross-party verification** | HMAC-SHA256 retained for local trail signing (correct); Ed25519 documented as the asymmetric upgrade path for full peer-verifiable signatures |

### Architecture

```
.swarm/federation/
  trusted_peers/<fingerprint>.json   # Layer 2: per-peer trust + scopes
  inbox/<ts>_<intent>_<fp8>.json    # inbound signed messages
  outbox/<ts>_<intent>_<fp8>.json   # outbound signed messages
  policy.md                          # Layer 1: global intent policy
  exports.md                         # what context this swarm shares
```

**Message flow:**
```
Peer A                                Peer B
  swarm federation export-id  ──────→  (out-of-band: email/git/Slack)
                               ←──────  swarm federation export-id
  swarm federation trust B_id.json
  swarm federation trust A_id.json     ←── (peer does the same)
  swarm federation send <fp> work_request --desc "..."
    → writes outbox/msg.json
  (deliver file to Peer B via git/shared dir)
                                         swarm federation inbox
                                         swarm federation apply inbox/msg.json
                                           → doorman_check() [L1+L2+L3]
                                           → add_item() if allowed
```

### CLI Commands

```
swarm federation init                    # create federation/ dirs
swarm federation export-id [--out FILE]  # share identity (public, safe to commit)
swarm federation trust PEER_IDENTITY.json [--name NAME] [--scopes SCOPES]
swarm federation revoke <fingerprint>
swarm federation peers
swarm federation send <fingerprint> <intent> [--desc TEXT] [--context TEXT]
swarm federation inbox
swarm federation apply MESSAGE.json [-y]
```

### Implementation Files
- `src/dot_swarm/federation.py` — 280 lines: `trust_peer()`, `doorman_check()`, `write_outbox()`, `read_inbox()`, `apply_inbox_message()`, `sign_federation_message()`, `verify_federation_message()`
- `src/dot_swarm/cli.py` — `swarm federation` command group (8 subcommands, ~200 lines)
- `tests/test_federation.py` — 34 tests
- `tests/test_signing.py` — 22 tests
- `tests/test_security.py` — 15 tests
- **No new dependencies** — stdlib only (hashlib, hmac, json, re)

### Oasis-X Alignment
- **MQ service**: Future upgrade path — federation messages transported over oasis-cloud MQ instead of file exchange
- **Auth service**: Federation identity can be tied to Oasis Auth JWT tokens for cross-org authentication
- **Sentinel service**: Sentinels could watch `federation/inbox/` and auto-react (Trigger: new inbox message → Analysis: parse intent → Reaction: `add_item()` or notify)

### OGP Full Upgrade Path

| Now (OGP-lite) | Full OGP |
|---|---|
| Identity via `export-id` (manual exchange) | Ed25519 public key, DNS-discoverable |
| Transport: git/file | HTTP/gRPC gateway |
| HMAC-SHA256 local trail signing | Ed25519 asymmetric (peers verify independently) |
| `trusted_peers/` files | Bilateral gateway handshake |
| Manual `apply` | Doorman auto-applies with approval UX |

**Outreach**: `.drafts/trilogy_outreach.txt` proposes a transport-agnostic federation profile spec to Trilogy AI so dot_swarm and OGP can remain aligned on identity and intent schema standards.

---

## 3. Task Scheduling & Agent/Computational Composition — IMPLEMENTED (SWC-013)

**Status**: Complete as of 2026-04-06. 63 tests passing (38 scheduler + 25 workflow).

### Motivation
Add time-driven and event-driven automation so agents can chain work without manual intervention. Aligned with swarms.ai orchestration patterns.

### Design Decisions

| Decision | Rationale |
|---|---|
| No daemon | Cron-style: `swarm schedule run-due` called by system crontab — simpler, no background process |
| Stdlib cron evaluator | No `croniter` dependency; custom 5-field parser handles `*`, `*/N`, `a-b`, `a,b`, `a-b/N` |
| Markdown-native storage | `schedules.md` + `workflows/*.md` — same pattern as queue.md, readable by any agent |
| Sequential halt on failure | Downstream steps skip with `skip_reason` in run log — preserves audit trail |
| `workflow_runs.jsonl` | Append-only run log; `workflow status` reads last entry per name |

### Scheduler (`scheduler.py`)

**Schedule types:**

| Type | Spec | Example |
|---|---|---|
| `cron` | 5-field expression | `0 */6 * * *` |
| `interval` | `Nm`/`Nh`/`Nd` | `6h`, `30m`, `2d` |
| `on:done` | `on:done ITEM-ID` | `on:done CLD-042` |
| `on:blocked` | `on:blocked ITEM-ID` | `on:blocked CLD-001` |

Event-driven schedules (`on:done`, `on:blocked`) are never fired by `run-due` — they are dispatched by `get_event_triggers()` which should be called from the `done`/`block` operation hooks (future integration point).

### Workflows (`workflows.py`)

Workflow files live in `.swarm/workflows/*.md` (already in `SwarmPaths`):

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
```

**Execution patterns:** `sequential` (halt on failure), `concurrent` (parallel threads), `conditional` (if-guarded steps), `mixture` (concurrent + agent diversity).

### CLI

```
swarm schedule list / add / remove / run / run-due
swarm workflow list / show / create / run / status
```

### Implementation Files
- `src/dot_swarm/scheduler.py` — 250 lines: `Schedule`, `add_schedule()`, `is_due()`, `_cron_is_due()`, `run_due()`, `get_event_triggers()`
- `src/dot_swarm/workflows.py` — 300 lines: `Workflow`, `WorkflowStep`, `run_workflow()`, `_run_sequential()`, `_run_concurrent()`, `_eval_condition()`, `workflow_status()`
- `src/dot_swarm/cli.py` — `swarm schedule` + `swarm workflow` groups (12 subcommands, ~300 lines)
- `tests/test_scheduler.py` — 38 tests
- `tests/test_workflows.py` — 25 tests
- **No new dependencies** — stdlib only

### Oasis-X Alignment
- **Sentinel service**: `[cron]` schedule ↔ Sentinel `trigger_type: cron`; workflow step `command` ↔ `analysis_type`; step `agent:` ↔ `reaction_type`
- **oasis-workers (ORG-021)**: dot_swarm workflows become the coordination layer for oasis-workers dispatch
- **oasis-ai (ORG-020)**: Workflow steps with `agent: bedrock` / `agent: claude` dispatch to the oasis-ai MCP server

---

## 4. swarms.ai Integration & PR Proposal — IMPLEMENTED (SWC-015)

**Status**: Complete as of 2026-04-06. 33 tests passing. PR guide at `docs/SWARMS_AI_PR_GUIDE.md`.

### Intersection Analysis (updated)

| swarms.ai Concept | dot_swarm Equivalent | Status |
|---|---|---|
| `Agent` (LLM wrapper) | `swarm ai` + `DotSwarmStateProvider` | ✓ Done — provider injects `.swarm/` context into any agent |
| `SequentialWorkflow` | `DotSwarmWorkflow` `pattern: sequential` | ✓ Done — markdown-native, 195 tests pass |
| `ConcurrentWorkflow` | `DotSwarmWorkflow` `pattern: concurrent` | ✓ Done — parallel threading |
| `MixtureOfAgents` | `DotSwarmWorkflow` `pattern: mixture` | ✓ Done — concurrent + per-step `agent:` routing |
| `AgentRearrange` | `swarm heal --fix` | ✓ Done |
| `SwarmRouter` | `swarm configure --via` | ✓ Done |
| `AOP` (Agent Orchestration Protocol) | OGP-lite federation | ✓ Done — different transport, same semantics |
| `SocialAlgorithms` | `StigmergicSwarm` | ✓ Done — indirect coordination |
| State persistence | `.swarm/` directory | ✓ Done — fills swarms.ai gap |
| Git audit trail | `swarm audit --trail` | ✓ Done — fills swarms.ai gap |

### PR Deliverables (all in `src/dot_swarm/swarms_provider.py`)

| Class | Standalone? | Description |
|---|---|---|
| `DotSwarmStateProvider` | Yes | Reads `.swarm/` → system prompt injection; applies AI JSON ops back |
| `DotSwarmWorkflow` | Yes (swarms.ai optional) | Loads `.swarm/workflows/*.md`; routes steps to registered agents |
| `DotSwarmTool` | Yes | Callable tool interface: `status/claim/done/add/memory/heal` |
| `StigmergicSwarm` | No (requires swarms) | Novel indirect coordination via `.swarm/` shared state |

### Test Coverage
- `tests/test_swarms_provider.py` — 33 tests (all standalone, no `swarms` dep required)
- Full PR guide: `docs/SWARMS_AI_PR_GUIDE.md`
- Proposed PR location: `swarms/integrations/dot_swarm/`

---

## Implementation Phases

### Phase 1: `swarm heal` (1-2 days)
- [ ] Implement `heal_report()` in `operations.py`
- [ ] Add `heal` CLI command
- [ ] Add `--fix` auto-correction mode
- [ ] Tests for alignment gap detection
- [ ] Update ARCHITECTURE.md

### Phase 2: Task Scheduling & Workflows (3-5 days)
- [ ] Define `schedules.md` format spec
- [ ] Implement `scheduler.py` (cron parsing, trigger dispatch)
- [ ] Define workflow markdown format spec
- [ ] Implement `workflows.py` (step parsing, sequential execution)
- [ ] Add CLI commands (`schedule`, `workflow`)
- [ ] Add MCP tools
- [ ] Tests for schedule evaluation and workflow execution

### Phase 3: OGP-Lite Federation (3-5 days)
- [ ] Implement `federation.py` (identity, signing, inbox/outbox)
- [ ] Add `federation` CLI command group
- [ ] Add MCP tools
- [ ] Define federation message format spec
- [ ] Tests for signing/verification roundtrip
- [ ] Document federation protocol in ARCHITECTURE.md

### Phase 4: swarms.ai PR (5-7 days)
- [ ] Implement `DotSwarmStateProvider`
- [ ] Implement `DotSwarmWorkflow` adapter
- [ ] Implement `DotSwarmTool`
- [ ] Implement `StigmergicSwarm` architecture
- [ ] Write tests compatible with swarms.ai test suite
- [ ] Write documentation for swarms.ai docs site
- [ ] Open PR with description and examples

---

## Oasis-X Service Intersection Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        dot_swarm (coordination layer)                │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌────────────────┐  │
│  │ swarm    │  │ schedules │  │ workflows  │  │ federation     │  │
│  │ heal     │  │ & cron    │  │ sequential │  │ OGP-lite       │  │
│  │          │  │           │  │ concurrent │  │ identity+trust │  │
│  └────┬─────┘  └─────┬─────┘  └──────┬─────┘  └───────┬────────┘  │
│       │              │               │                 │           │
└───────┼──────────────┼───────────────┼─────────────────┼───────────┘
        │              │               │                 │
        ▼              ▼               ▼                 ▼
┌───────────────────────────────────────────────────────────────────┐
│                    oasis-cloud services                            │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ Sentinel     │  │ AI Service   │  │ MQ Service   │            │
│  │ ─────────── │  │ ──────────── │  │ ──────────── │            │
│  │ Trigger→     │  │ Bedrock      │  │ MQTT pub/sub │            │
│  │ Analysis→    │  │ inference    │  │ event-driven │            │
│  │ Reaction     │  │ token tiers  │  │ communication│            │
│  │              │  │              │  │              │            │
│  │ ↕ heal maps  │  │ ↕ workflows  │  │ ↕ federation │            │
│  │   to ontology│  │   dispatch   │  │   transport  │            │
│  │   consistency│  │   to AI svc  │  │   upgrade    │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ Data Service │  │ Auth Service │  │ oasis-workers│            │
│  │ ──────────── │  │ ──────────── │  │ (ORG-021)    │            │
│  │ Collections  │  │ JWT tokens   │  │ ──────────── │            │
│  │ Sources      │  │ RBAC         │  │ Generalized  │            │
│  │ Measurements │  │              │  │ agent/worker │            │
│  │              │  │ ↕ federation │  │ code          │            │
│  │ ↕ categorical│  │   identity   │  │              │            │
│  │   ontology   │  │   binding    │  │ ↕ dot_swarm  │            │
│  │   backing    │  │              │  │   workflows  │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│                    swarms.ai (external FOSS)                      │
│                                                                    │
│  DotSwarmStateProvider  → persistent state for swarms.ai agents   │
│  DotSwarmWorkflow       → markdown→SequentialWorkflow adapter     │
│  DotSwarmTool           → MCP tool for .swarm/ operations         │
│  StigmergicSwarm        → novel coordination architecture         │
└───────────────────────────────────────────────────────────────────┘
```

---

## Open Questions for Review

1. **Federation signing**: Use `PyNaCl` (ed25519, proper crypto) or `hashlib` HMAC (simpler, stdlib-only)? PyNaCl is more aligned with real OGP but adds a dependency.

2. **Scheduler execution**: Should schedules be evaluated by a long-running daemon (`swarm scheduler start`) or by a cron job that calls `swarm schedule tick`? The daemon approach is more responsive but requires process management; the cron approach is simpler and more unix-native.

3. **Workflow agents**: When a workflow step says `agent: bedrock`, should it use `swarm ai` (existing CLI) or directly invoke the LLM? Using `swarm ai` keeps everything in the dot_swarm protocol but adds overhead.

4. **swarms.ai PR scope**: Start with just `DotSwarmStateProvider` (smallest useful contribution) or go for the full `StigmergicSwarm` (more ambitious, higher impact)?

5. **Phase ordering**: The plan orders phases by complexity. Should we instead prioritize based on Oasis-X roadmap alignment (e.g., federation first because of oasis-workers)?

---

## Next Steps

After this plan is reviewed, edited, and approved:
1. Update `.swarm/queue.md` with implementation work items
2. Update `.swarm/state.md` with new focus
3. Begin Phase 1 implementation (`swarm heal`)
