# State — dot_swarm

**Last touched**: 2026-04-19T00:00Z by human-ML
**Current focus**: Multi-agent tooling complete — spawn, crawl, retry logic, docs
**Active items**: (none)
**Blockers**: PyPI Trusted Publishing not yet configured (manual step for SWC-003)
**Ready for pickup**: SWC-021 (supervisor brief), SWC-024 (merge queue), SWC-007, SWC-008, SWC-009

---

## Handoff Note

**Spawn, crawl, retry logic complete (2026-04-19)**:
swarm spawn: tmux worker/role launcher with auto-claim, SWARM_AGENT_ID/ROLE env, opencode|claude|ollama|bedrock.
swarm crawl: crawl_directory() walks tree, skips .swarm/ divisions, writes Directory Map to context.md.
WorkItem.max_retries: task-level inspector retry override; block-on-exhaust replaces watchdog role.
Watchdog subsumed into reopen_item() auto-BLOCK; Librarian subsumed into swarm crawl.
Docs updated: ROLES.md, CLI_REFERENCE.md (spawn, crawl, max_retries, updated interaction map).
SWC-020 (watchdog), SWC-022 (librarian), SWC-023 (spawn), SWC-025 (crawl+retries) all DONE.

**Agent roles + multi-agent tooling implemented (2026-04-18)**:
New files: `src/dot_swarm/roles.py` — RoleConfig, enable/disable/load/list_roles,
validate_proof, check_escalation. Four roles defined: inspector, watchdog, supervisor, librarian.
WorkItem model gains `proof:` and `inspect_fails:` fields (parse + serialize).
operations.py: `ready_items()` (bd-ready equivalent), `reopen_item()` (inspector fail path).
CLI additions: `swarm ready [--json]`, `swarm role list/enable/disable/show`,
`swarm inspect <id> --pass|--fail --reason`, `swarm partial --proof`, `swarm done --force`.
mkdocs.yml fixed: site_url/repo_url updated from SwarmCity → dot_swarm.
Tests: 195 still passing (no new test files yet — SWC-019 still needs test coverage).
Next: write tests for roles.py + new CLI commands, then implement SWC-020 (watchdog escalation log).

**Phase 1 implementation complete (2026-04-06)**:
New files created:
- `src/dot_swarm/signing.py` — HMAC-SHA256 identity, pheromone trail.log, blocked_peers.json
- `src/dot_swarm/security.py` — 18-pattern adversarial content scanner (CRITICAL/HIGH/MEDIUM)
- `src/dot_swarm/swarms_provider.py` — DotSwarmStateProvider + StigmergicSwarm (swarms.ai bridge)

CLI additions:
- `swarm heal` — full alignment + security scan + trail verification + memory logging + --fix quarantine
- `swarm audit` — enhanced: --pending --security --drift --trail --full flags
- `swarm ai --chain` — auto-chains AI invocations; --max-steps N; signs each batch in trail.log
- `swarm init` — now auto-generates signing identity + .swarm/.gitignore

Phase dependency order: SWC-010/011 (crypto+heal) → SWC-012 (docs) → SWC-013 (scheduling) → SWC-014 (federation uses SWC-010 crypto) → SWC-015 (swarms.ai PR, uses SWC-013 workflows)

**Research track (from 2026-04-03)**: SWC-007 (stigmergy paper), SWC-008 (boids paper), SWC-009 (BoidRunner).

**Distribution still blocked**: configure Trusted Publishing (OIDC) on PyPI at
pypi.org/manage/project/dot-swarm/settings/publishing/ for repo MikeHLee/dot_swarm, workflow
publish-pypi.yml. Then tag v0.3.0 → publish workflow fires → Homebrew SHA256 available.

