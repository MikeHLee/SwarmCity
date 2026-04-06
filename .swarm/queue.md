# Queue — SwarmCity (Organization Level)

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
