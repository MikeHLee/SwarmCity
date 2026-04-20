# Queue — dot_swarm (Organization Level)

Items are listed in priority order within each section.
Item IDs: `SWC-<3-digit-number>` — assigned sequentially, never reused.

---

## Active

(no active items)

## Pending

<!-- ═══════════════ INTEGRATION: swarms.ai + oasis-x ═══════════════ -->

- [x] [SWC-013] [DONE] Phase 2: schedules.md + workflow composition (cron-based)
      project: integration-swarms-ai
      priority: high
      completed: 2026-04-06
      notes: scheduler.py: Schedule dataclass, add_schedule(), is_due(), _cron_is_due() (stdlib, no croniter),
             run_due(), get_event_triggers(). Types: cron/interval/on:done/on:blocked.
             workflows.py: Workflow/WorkflowStep/StepResult/WorkflowRun, load/create/run_workflow(),
             _run_sequential() (halt on failure + skip propagation), _run_concurrent() (threading),
             _eval_condition() (step1.ok guards), workflow_status() from workflow_runs.jsonl.
             CLI: swarm schedule list/add/remove/run/run-due + swarm workflow list/show/create/run/status.
             Tests: test_scheduler.py (38) + test_workflows.py (25) = 63 new. Total suite: 162 passing.
             No new dependencies — stdlib only. Cron decision: no daemon, no croniter.

- [x] [SWC-014] [DONE] Phase 3: OGP-lite federation layer
      project: integration-swarms-ai
      priority: medium
      completed: 2026-04-06
      notes: federation.py implemented: trust_peer(), doorman_check() (3-layer),
             write_outbox(), read_inbox(), apply_inbox_message().
             CLI: swarm federation init/export-id/trust/revoke/peers/send/inbox/apply.
             Tests: test_federation.py (34 tests, 100% pass). test_signing.py (22 tests).
             test_security.py (15 tests). 71 total across all new modules.
             OGP learnings applied: identity=fingerprint (not path), persist-before-return,
             doorman never trusts claimed from_fingerprint — always looks up from stored record.
             Signing note: HMAC-SHA256 for local trail integrity; Ed25519 upgrade path documented.
             Outreach draft: .drafts/trilogy_outreach.txt (transport-agnostic profile proposal).

- [x] [SWC-015] [DONE] Phase 4b: StigmergicSwarm contribution to swarms.ai
      project: integration-swarms-ai
      priority: medium
      completed: 2026-04-06
      notes: swarms_provider.py extended with DotSwarmWorkflow (from_markdown, from_swarm_dir,
             add_agent() fluent, run() with sequential halt-on-failure + condition guards + agent routing)
             and DotSwarmTool (callable: status/claim/done/add/memory/heal ops).
             StigmergicSwarm already implemented. All four classes in swarms_provider.py.
             Tests: test_swarms_provider.py (33 tests, all standalone, no swarms dep).
             PR guide: docs/SWARMS_AI_PR_GUIDE.md. Proposed: swarms/integrations/dot_swarm/.
             Total test suite: 195 passing.

<!-- ═══════════════ RESEARCH INITIATIVES ═══════════════ -->

- [ ] [SWC-007] [OPEN] Write paper: stigmergy for AI agent coordination → AAMAS / LLM-agents workshop
      project: research-stigmergy
      priority: high
      notes: Novel claim — first filesystem-native stigmergy protocol for multi-agent AI dev teams.
             Core argument: pheromone trail (state.md) + decay (audit) + no-server coordination
             beats centralized trackers for latency and resilience. Grounded in Grassé 1959,
             Dorigo ACO, Bonabeau et al. Target venues (in priority order):
               1. AAMAS 2027 — full paper, agent coordination track
               2. NeurIPS/ICLR 2026-27 — LLM-based agents workshop (short paper, faster turnaround)
               3. AAAI 2027 — AI systems track if AAMAS misses
             Outline:
               § 1. Introduction + motivation
               § 2. Related work
                    - Stigmergy: Grassé 1959, Theraulaz & Bonabeau 1999, Bonabeau et al. 1999
                    - ACO: Dorigo, Maniezzo & Colorni 1996; Parunak 1997
                    - Git-native project tools: GitHub Issues, Linear, Jira (comparison targets)
                    - Multi-agent AI frameworks: swarms.ai, AutoGen, CrewAI (coordination models)
                    - Federated inter-agent protocols: OGP (Proctor 2026) — see §4 below
               § 3. Architecture (stigmergy primitives, pheromone decay, hierarchical colony)
               § 4. Security under adversarial conditions [NEW — OGP-motivated]
                    - Trust-the-claim failure mode: attacker controls message body → impersonates peer
                    - Same attack surface in both inter-agent federation AND LLM prompt injection
                    - OGP post-mortem (Proctor 2026) as case study: identity=hostname:port bug,
                      persist-before-return race, implicit trust scope
                    - dot_swarm mitigations: fingerprint-indexed identity, signed trail, 18-pattern
                      adversarial scanner, three-layer doorman (policy → peer record → runtime)
                    - Key claim: stigmergic systems are uniquely vulnerable to environment poisoning
                      (a malicious agent writes to the shared medium) — and uniquely easy to audit
                      (every write is a file change, detectable by drift check)
               § 5. Evaluation (latency vs GitHub Issues/Jira, drift detection accuracy)
               § 6. Discussion (limits: Unix-only locking, Windows gap, no real-time notification)
             References to add:
               Proctor, D. (2026). "Case Study: Building a Protocol in the Age of AI."
               Trilogy AI Substack. https://trilogyai.substack.com/p/case-study-building-a-protocol-in
             Needs: comparative experiment section + at least one real multi-agent case study.

- [ ] [SWC-008] [OPEN] Write paper: seamless swarm looping via trajectory tracking + Hermite splines → SIGGRAPH / Eurographics
      project: research-boids
      priority: high
      notes: Novel pipeline for perfectly seamless animated swarm GIFs / real-time loops:
               1. Jerk + snap constraints (limits da/dt and d²a/dt²) — borrowed from minimum-jerk
                  trajectory planning (Flash & Hogan 1985) but applied to Boids steering forces
               2. Trajectory-capture looping — record launch phase, use as landing attractor
               3. Hermite spline C1-smooth final approach — velocity-continuous return to origin
             Key metric: loop position error reduced 2.10 → 0.0057 px (99.7% improvement).
             Target venues (in priority order):
               1. SIGGRAPH 2027 Talks — strongest fit, procedural animation; no full paper required
               2. Eurographics 2027 short papers — 4 pages, peer reviewed
               3. Motion, Interaction and Games (MIG) 2026 — deadline sooner, relevant audience
             Needs: ablation study (remove each constraint, measure loop error + perceptual score),
             user study or video comparison, runtime benchmark (pure Python + NumPy baseline).
             Depends on: SWC-009 (BoidRunner refactor gives clean eval harness).

- [ ] [SWC-009] [OPEN] Launch BoidRunner: technical blog post → browser simulator / game
      project: boidrunner
      priority: medium
      notes: Phased plan —
             Phase 1 · Blog post (2-3 weeks): publish on personal site or dev.to / Hacker News.
               Lead with the animated GIFs. Explain trajectory tracking, jerk/snap constraints,
               Hermite spline approach. Include loop-error chart (2.10 → 0.0057). This drives
               awareness and gathers feedback before committing to a package API.
             Phase 2 · Standalone package (after blog): refactor gen_logo.py into a clean
               `Swarm` class with normalized units (canvas-independent), expose trajectory-loop
               API, publish to PyPI as `boidrunner`. Zero deps beyond NumPy + Pillow.
             Phase 3 · Browser simulator / game (stretch): port to JS/TS (or Pyodide/WASM) for
               interactive demo. Users tune weights (sep, ali, coh, jerk-limit) and watch loop
               quality change in real time. Could evolve into a casual web game (herd the boids,
               race to best loop error, etc.).
             Decision: blog-first, no package until API is validated by readers.
             Blocks: SWC-008 (needs eval harness from Phase 2 refactor).

<!-- ═══════════════ AGENT ROLES + MULTI-AGENT TOOLING ═══════════════ -->

- [x] [SWC-016] [DONE · 2026-04-18T00:00Z] Fix mkdocs.yml stale SwarmCity → dot_swarm URLs
      project: docs
      priority: high
      notes: site_url, repo_url, repo_name all updated; gh-pages branch already exists on MikeHLee/dot_swarm

- [ ] [SWC-017] [OPEN] swarm ready — dependency-aware work discovery (like bd ready)
      project: cli-roles
      priority: high
      notes: DONE in this session — lists OPEN pending items with all deps completed.
             swarm ready / swarm ready --json. See operations.ready_items().

- [ ] [SWC-018] [OPEN] Role system infrastructure: roles.py + swarm role enable/disable/show/list
      project: cli-roles
      priority: high
      notes: DONE in this session — roles.py: RoleConfig, enable_role, disable_role, load_role,
             is_role_enabled, list_roles, validate_proof, check_escalation.
             CLI: swarm role list/enable/disable/show.
             Roles stored in .swarm/roles/<name>.json (toggled without touching queue.md).

- [ ] [SWC-019] [OPEN] Inspector role — proof-of-work gate, swarm inspect --pass/--fail
      project: cli-roles
      priority: high
      notes: DONE in this session — WorkItem gains proof: + inspect_fails: fields.
             swarm partial <id> --proof "branch:X commit:Y tests:N/N" (worker attaches evidence).
             swarm done now blocked when inspector enabled + proof missing (--force to override).
             swarm inspect <id> --pass|--fail --reason <text> (inspector agent verifies).
             reopen_item() in operations.py: clears proof, increments inspect_fails, moves to OPEN.
             Escalates to watchdog after max_iterations (default 3) if watchdog role is enabled.

- [x] [SWC-020] [DONE · 2026-04-19T00:00Z] Watchdog role — escalate stuck items to human when worker+inspector loop
      project: cli-roles
      priority: medium
      notes: Subsumed into inspector retry loop. reopen_item() now auto-BLOCKs when inspect_fails
             >= effective max_retries (task-level overrides role-level). Blocked items surface in
             swarm audit/status naturally. swarm spawn --role watchdog opens a live monitor window.

- [ ] [SWC-021] [OPEN] Supervisor role — holistic progress view + human-director briefs
      project: cli-roles
      priority: medium
      notes: swarm supervisor report (all active items + phase progress across queue sections),
             swarm supervisor brief --format md (structured summary for human director).
             Should aggregate across ascend/descend hierarchy too.

- [x] [SWC-022] [DONE · 2026-04-19T00:00Z] Librarian role — catalog directory tree into .swarm/ context + queue
      project: cli-roles
      priority: medium
      notes: Subsumed into swarm crawl command. crawl_directory() in operations.py walks tree,
             skips existing .swarm/ divisions, appends Directory Map to context.md.
             swarm crawl --create-items generates OPEN queue items for uncatalogued dirs.
             Combined with swarm heal this replaces the librarian role entirely.

- [x] [SWC-023] [DONE · 2026-04-19T00:00Z] tmux worker spawning — swarm spawn <id> [--agent opencode|claude|ollama]
      project: cli-roles
      priority: high
      notes: Implemented. swarm spawn SWC-042 --agent opencode|claude|ollama|bedrock.
             Auto-creates tmux session, opens named window, sets SWARM_AGENT_ID/SWARM_ITEM_ID/SWARM_ROLE.
             Auto-claims item unless --no-claim. Role agents: swarm spawn --role inspector|supervisor|watchdog.
             Dependency checks: tmux 3.0+ and chosen agent CLI on PATH.

- [x] [SWC-025] [DONE · 2026-04-19T00:00Z] Task-level max_retries + swarm crawl command
      project: cli-roles
      priority: high
      notes: WorkItem.max_retries field (0=use role default, >0=task override).
             swarm add --max-retries N sets per-task inspector retry limit.
             reopen_item() uses effective_max = max(task, role) with block-on-exhaust.
             swarm crawl: crawl_directory() in operations.py, --depth/--create-items/--dry-run.
             Watchdog and Librarian roles subsumed; simpler architecture overall.

<!-- ═══════════════ CLI IMPROVEMENTS ═══════════════ -->

- [x] [SWC-026] [DONE · 2026-04-19] swarm trail visible/invisible — gitignore-based .swarm sharing toggle
      project: cli-core
      priority: high
      notes: Implemented as `swarm trail` group with status/invisible/visible subcommands.
             swarm init now defaults to invisible (--visible flag to opt in).
             _repo_gitignore() walks up to nearest .git root. _set_trail_visibility()
             adds/removes .swarm/ entry with explanatory comment. Docs: CLI_REFERENCE.md.

- [x] [SWC-027] [DONE · 2026-04-19] Tighten init/crawl/explore coupling
      project: cli-core
      priority: medium
      notes: No redundancy to remove — init creates blank .swarm/, crawl populates context.md
             with Directory Map, explore is read-only display. But they should be coupled:
             - swarm init should offer to run swarm crawl immediately after (--crawl flag)
             - swarm crawl should detect dirs that need init and warn/offer to run it
             - swarm explore should surface crawl coverage (which dirs have been catalogued)
             Goal: init → crawl → explore forms a coherent onboarding arc.

- [x] [SWC-028] [DONE · 2026-04-19] Ollama AI backend integration (alongside Bedrock)
      project: ai-features
      priority: high
      notes: swarm spawn --agent ollama already launches ollama in tmux as a worker tool,
             but there is no ollama equivalent to the Bedrock API backend in ai_ops.py.
             Add OllamaBackend to ai_ops.py: ollama REST API (localhost:11434/api/chat),
             model selection via swarm configure --provider ollama --model llama3.2,
             streaming responses, same tool-call interface as BedrockBackend.
             Also consider: LM Studio (compatible API), vLLM, Groq, Anthropic direct.
             Provider abstraction: unify under AbstractAIBackend so swarm ai works
             identically regardless of backend.

- [x] [SWC-029] [DONE · 2026-04-19] Document opencode+tmux multi-agent workflow end-to-end
      project: docs
      priority: high
      notes: Full spawn→claim→implement→proof→inspect→merge flow is implemented but
             undocumented end-to-end. Need a dedicated workflow guide:
             1. swarm role enable inspector --max-iterations 3
             2. swarm spawn SWC-042 --agent opencode  (worker tmux window, auto-claim)
             3. Worker reads BOOTSTRAP.md, implements, runs tests
             4. swarm partial SWC-042 --proof "branch:X commit:Y tests:N/N"
             5. swarm spawn --role inspector  (second tmux window)
             6. swarm inspect SWC-042 --pass|--fail
             7. swarm done / auto-block on exhaust
             Also document: env vars set in each window (SWARM_AGENT_ID/ITEM_ID/ROLE),
             which swarm commands to enable (role enable inspector + spawn deps: tmux 3.0+).
             Open question: add support for "pi" agentic coding harness? (clarify what
             "pi agentic" refers to — Raspberry Pi edge deployment? pi.ai terminal agent?
             Other? — pending user clarification before scoping.)

- [x] [SWC-030] [DONE · 2026-04-19] README + docs: security section overhaul with benefits AND vulnerabilities
      project: docs
      priority: high
      notes: Current security section is thin. Expand with:
             BENEFITS: HMAC-SHA256 per-swarm identity; 18-pattern adversarial scanner
             (CRITICAL/HIGH/MEDIUM); signed trail.log; swarm heal cross-validates all
             .swarm/ files; pheromone decay flags stale claims; cross-swarm poisoning
             is extremely hard due to cryptographic stamps + audit chain.
             VULNERABILITIES (honest disclosure): (1) Git-sharing = trail-sharing —
             pushing a repo exposes full swarm history unless trail is invisible.
             (2) HMAC signing is local-trust only (no PKI); a compromised swarm key
             breaks trail integrity for that swarm. (3) No real-time cross-network
             federation yet — federation is file-based OGP-lite, not live. (4) LLM
             content in .swarm/ files (memory.md, notes) is trust-boundary — an
             agent writing adversarial content to the shared medium can influence
             other agents reading it (mitigated by scanner but not eliminated).
             Add FUTURE: live networked federation across swarms (planned if userbase
             warrants it). Existing gitignore toggle (SWC-026) as the near-term fix.

- [x] [SWC-031] [DONE] Replace oasis-x specific examples in docs with rich generic examples
      project: docs
      priority: medium
      completed: 2026-04-19
      notes: docs/index.md + README.md: claim pattern block → API-042/043/041 (rate limiter,
             distributed tracing, auth middleware migration); quick start → API-001; spawn
             examples → API-042 with rate-limiter-specific proof strings.
             docs/CLI_REFERENCE.md: global options path → api-service; all CLD-*/SWC-* work
             item IDs → API-*; schedule/workflow triggers → API-041/042/043; workflow name →
             rate-limiter-rollout; inspect examples → API-042; spawn window → API-042;
             crawl output → api-service/services/auth/services/payments; Item ID Convention
             table → generic SaaS divisions (API/AUTH/DASH/MOB/FW/DOC/INF/LAB/SWC).

- [ ] [SWC-032] [OPEN] Move collaboration/integration notes from docs into .swarm trail; make invisible
      project: docs
      priority: medium
      notes: SWARMS_AI_PR_GUIDE.md, INTEGRATION_PLAN.md, PLATFORM_SETUP.md contain
             internal oasis-x operating info and integration notes. Move relevant
             content into: .swarm/memory.md (decisions + rationale), .swarm/context.md
             (architecture notes), .swarm/queue.md (open integration work items).
             After migration: remove or heavily redact those docs pages (or mark
             nav_exclude: true, which is already done).
             Then run `swarm trail invisible` (SWC-026) to add .swarm/ to .gitignore
             so the trail is private by default.
             Also: move oasis-x portfolio/division structure examples into the
             oasis-x .swarm directory, not the dot_swarm docs.

- [ ] [SWC-024] [OPEN] Merge queue (lightweight Refinery) — serialize concurrent branch merges
      project: cli-roles
      priority: low
      notes: Gastown's Refinery role manages merge queue to prevent parallel worker collisions.
             dot_swarm equivalent: .swarm/merge_queue.md + swarm merge enqueue/next/pop.
             Lower priority since single-master git workflows mostly avoid this problem.

<!-- ═══════════════ CORE ARCHITECTURE + REPO STANDARDS ═══════════════ -->

- [ ] [SWC-033] [OPEN] Implement Conflict-Free Concurrency Mechanism (claims/ directory)
      project: architecture
      priority: high
      notes: Transition to append-only file structure (.swarm/claims/) to avoid Git merge conflicts.
             Update read protocols to dynamically resolve concurrent claims. [ARCH-001]

- [x] [SWC-034] [DONE · 2026-04-20] Mandate MCP Server for Agent Interactions
      project: architecture
      priority: high
      notes: Expand MCP server implementation. Enforce agent interaction via tools rather than
             raw file editing to prevent Markdown parsing brittleness. [ARCH-002]

- [x] [SWC-035] [DONE · 2026-04-20] Add Open Source License (MIT or Apache 2.0) Add Open Source License (MIT or Apache 2.0)
      project: repo-standards
      priority: high
      notes: Add LICENSE file to root to unblock corporate and widespread adoption. [REPO-001]

- [x] [SWC-036] [DONE · 2026-04-20] Establish Governance & Contribution Guidelines Establish Governance & Contribution Guidelines
      project: repo-standards
      priority: high
      notes: Create CONTRIBUTING.md and .github/ISSUE_TEMPLATE files. [REPO-002]

- [x] [SWC-037] [DONE · 2026-04-20] Expand CI/CD Matrix (Linux, macOS, Windows) Expand CI/CD Matrix (Linux, macOS, Windows)
      project: repo-standards
      priority: high
      notes: Ensure GitHub Actions run tests across all major OSes for path handling. [REPO-003]

<!-- ═══════════════ FEATURES + FUTURE DIRECTIONS ═══════════════ -->

- [x] [SWC-038] [DONE · 2026-04-20] Native CI/CD Integration: GitHub Action for audit/heal Native CI/CD Integration: GitHub Action for audit/heal
      project: features
      priority: medium
      notes: Create/publish official Action to ensure protocol files haven't drifted.

- [x] [SWC-039] [DONE · 2026-04-20] Competitive Task Resolution (Parallel Execution)
      project: features
      priority: medium
      notes: Implement intentional duplicate claims [COMPETING] or [REVIEW].
             Inspector/Supervisor agents vote on winning implementation.

- [x] [SWC-040] [DONE · 2026-04-20] Visual Protocol Diagrams (Mermaid.js)
      project: docs
      priority: medium
      notes: Add diagrams to README demonstrating stigmergy feedback loop. [DOCS-001]

- [x] [SWC-041] [DONE · 2026-04-20] Explicitly list system-level prerequisites (Git, tmux) Explicitly list system-level prerequisites (Git, tmux)
      project: docs
      priority: medium
      notes: Add to Quick Start/Installation guide to prevent command-not-found errors. [DOCS-002]

<!-- ═══════════════ DISTRIBUTION ═══════════════ -->

- [ ] [SWC-003] [OPEN] Configure Trusted Publishing (OIDC) on PyPI
      Manual step: pypi.org/manage/project/dot-swarm/settings/publishing/
      Repo: MikeHLee/dot_swarm · Workflow: publish-pypi.yml · Environment: (none)
      Blocks: SWC-004
      project: distribution

- [ ] [SWC-004] [OPEN] Tag and publish v0.3.0 to PyPI
      Run: git tag v0.3.0 && git push origin v0.3.0
      GitHub Actions workflow fires automatically on v* tag push
      Depends on: SWC-003
      project: distribution

- [ ] [SWC-005] [OPEN] Update Homebrew formula for dot-swarm v0.3.0
      File: swarm-city.rb.template
      - Rename package URL from swarm-city → dot-swarm
      - Bump version to 0.3.0
      - Replace SHA256 placeholder with real hash from PyPI tarball
      Depends on: SWC-004 (need live PyPI tarball for SHA256)
      project: distribution

- [ ] [SWC-006] [OPEN] Submit Homebrew formula to tap
      Decision needed: publish to homebrew-core or host own tap (e.g. MikeHLee/homebrew-dot-swarm)
      Depends on: SWC-005
      project: distribution

## Done

- [x] [SWC-012] [DONE · 2026-04-06T14:00Z] Phase 1c: docs/CLI_REFERENCE.md — heal, audit --full, ai --chain, security model, swarms.ai integration
      project: integration-swarms-ai

- [x] [SWC-011] [DONE · 2026-04-06T14:00Z] Phase 1b: swarm heal + swarm audit + swarm ai --chain + init identity
      project: integration-swarms-ai

- [x] [SWC-010] [DONE · 2026-04-06T14:00Z] Phase 1a: signing.py (HMAC-SHA256) + security.py (18-pattern scanner) + swarms_provider.py (DotSwarmStateProvider + StigmergicSwarm)
      project: integration-swarms-ai

- [x] [SWC-001] [DONE · 2026-03-31T15:00Z] GUI for visualizing swarm trails in a GitHub repo
      project: visualizer
- [x] [SWC-002] [DONE · 2026-03-31T14:30Z] CLI commands `up` and `down` to manage alignment/relation of work items
      project: alignment
- [x] [SWC-003-pre] [DONE · 2026-04-01] Sync package name + version after dot_swarm rename
      Updated install docs (swarm-city → dot-swarm), versions (0.2.0 → 0.3.0), publish workflow
      Commit: 7953ea2
      project: distribution
