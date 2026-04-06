# State — SwarmCity

**Last touched**: 2026-04-06T16:30Z by cascade
**Current focus**: All integration phases complete (SWC-013/014/015). 195 tests passing.
**Active items**: (none)
**Blockers**: PyPI Trusted Publishing not yet configured (manual step for SWC-003)
**Ready for pickup**: SWC-007 (stigmergy paper — §4 security section now scoped; OGP citation added), SWC-008, SWC-009

---

## Handoff Note

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

