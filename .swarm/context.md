# Context — dot_swarm

**Level**: Organization
**Division code**: SWC
**Last updated**: 2026-03-31

## What This Division Is

dot_swarm is a minimal, git-native, markdown-first agent orchestration system for multi-repo organizations. It uses a nature-inspired "pheromone trail" approach where coordination state lives in `.swarm/` directories as plain markdown files.

## Architecture Constraints

1. **Git-Native**: All state must live in markdown files within the repository. Git is the only database.
2. **Stigmergic Coordination**: Agents communicate by modifying the environment (state.md), not by direct messaging.
3. **Decentralized**: No central server or coordinator is required.
4. **Agent-Agnostic**: Any AI agent or human developer can read and write the `.swarm/` files.

## Current Focus Areas

1. **Distribution (Phase 4)**: Publishing dot-swarm to PyPI and Homebrew. PyPI workflow is in place; blocked on Trusted Publishing OIDC setup (SWC-003 → SWC-006).
2. **Research — Stigmergy (SWC-007)**: Writing the AAMAS / LLM-agents workshop paper. Core claim: first filesystem-native stigmergy protocol for multi-agent AI dev teams. Needs comparative experiment and at least one real multi-agent case study.
3. **Research — Boids Looping (SWC-008)**: Writing the SIGGRAPH Talks / Eurographics short paper. Core contribution: jerk + snap constraints + trajectory-capture looping + Hermite C1 approach, achieving 99.7% reduction in loop error. Needs ablation study; depends on BoidRunner refactor for eval harness.
4. **BoidRunner (SWC-009)**: Phased launch — (1) technical blog post leading with animated GIFs and loop-error chart, (2) standalone PyPI package with clean `Swarm` API, (3) browser-based interactive simulator / casual game.
5. **Swarm Visualizer**: GUI for visualizing swarm trails — complete.
7. **Core Architecture (ARCH-001/002)**: Transitioning to append-only claim files (`.swarm/claims/`) to eliminate Git merge conflicts (SWC-033). Mandating MCP server for agent interactions to ensure protocol safety and Markdown integrity (SWC-034).
8. **Repository & Community Standards (REPO-001/002/003)**: Adding Open Source License (SWC-035), establishing governance/CONTRIBUTING.md (SWC-036), and expanding CI/CD matrix to Linux/macOS/Windows (SWC-037).
6. **Hierarchical Alignment**: CLI commands (`up` and `down`) — complete.
