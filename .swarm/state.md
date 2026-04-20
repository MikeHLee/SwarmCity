# State — dot_swarm

**Last touched**: 2026-04-20T17:57Z by Gemini-CLI
**Current focus**: Docs migrated to Jekyll/just-the-docs; README overhauled; roadmap expanded
**Active items**: (none)
**Blockers**: PyPI Trusted Publishing not yet configured (manual step for SWC-003)
**Ready for pickup**: SWC-033, SWC-034, SWC-035, SWC-036, SWC-037, SWC-026 (trail visibility toggle), SWC-028 (ollama backend), SWC-030 (security docs), SWC-021, SWC-007, SWC-008, SWC-009

---

## Handoff Note

**CI/CD & Compatibility Fixes (2026-04-20)**:
- Fixed Windows compatibility (optional `fcntl` import and flock guard).
- Added `anyio` to CI dependencies.
- Updated `resolve_claims` to handle `COMPETING` and `REVIEW` states.
- Fixed version inconsistency in `cli.py`.
- Version bump to 0.3.3.
