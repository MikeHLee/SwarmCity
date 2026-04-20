# State — dot_swarm

**Last touched**: 2026-04-20T17:03Z by Gemini-CLI
**Current focus**: Docs migrated to Jekyll/just-the-docs; README overhauled; roadmap expanded
**Active items**: (none)
**Blockers**: PyPI Trusted Publishing not yet configured (manual step for SWC-003)
**Ready for pickup**: SWC-033, SWC-034, SWC-035, SWC-036, SWC-037, SWC-026 (trail visibility toggle), SWC-028 (ollama backend), SWC-030 (security docs), SWC-021, SWC-007, SWC-008, SWC-009

---

## Handoff Note

**CI/CD Fixes & Version Bump (2026-04-20)**:
- Removed Python 3.10 from CI matrix (min version is 3.11).
- Added `anyio` to test dependencies.
- Made `tests/test_mcp.py` resilient to missing `mcp` module.
- Version bump to 0.3.2.
