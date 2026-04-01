# Context — SwarmCity

**Level**: Organization
**Division code**: SWC
**Last updated**: 2026-03-31

## What This Division Is

SwarmCity is a minimal, git-native, markdown-first agent orchestration system for multi-repo organizations. It uses a nature-inspired "pheromone trail" approach where coordination state lives in `.swarm/` directories as plain markdown files.

## Architecture Constraints

1. **Git-Native**: All state must live in markdown files within the repository. Git is the only database.
2. **Stigmergic Coordination**: Agents communicate by modifying the environment (state.md), not by direct messaging.
3. **Decentralized**: No central server or coordinator is required.
4. **Agent-Agnostic**: Any AI agent or human developer can read and write the `.swarm/` files.

## Current Focus Areas

1. **Swarm Visualizer**: GUI for visualizing swarm trails in a GitHub repo to provide better visibility into agent activity.
2. **Hierarchical Alignment**: CLI commands (`up` and `down`) to manage alignment and relation of work items across parent and child directories/repositories.
