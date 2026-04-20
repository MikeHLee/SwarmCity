# Contributing to dot_swarm

Welcome! Whether you are a human or an AI agent, we appreciate your interest in contributing to `dot_swarm`. 

`dot_swarm` is a stigmergy-based orchestration system, which means our coordination happens primarily through the environment (the `.swarm/` directory) and Git.

## Getting Started

1.  **Fork the repository** and clone it locally.
2.  **Initialize the swarm**: Run `swarm init` if you are starting a new project, or `swarm trail visible` to see the existing coordination trail.
3.  **Find a task**: Use `swarm ready` to find open tasks that are unblocked.
4.  **Claim a task**: Use `swarm claim <ID>` to announce you are working on it.

## Contribution Workflow

### For Humans

1.  **Create a branch**: `git checkout -b feature/your-feature-name`.
2.  **Implementation**: Make your changes and add tests.
3.  **Verify**: Ensure all tests pass (`pytest`).
4.  **Submit a PR**: Open a Pull Request against the `main` branch.

### For AI Agents

1.  **Spawn a worker**: Use `swarm spawn <ID> --agent <your-agent-type>`.
2.  **Implement and verify**: Follow the internal `dot_swarm` protocol for implementation and testing.
3.  **Proof of Work**: Attach proof of your work using `swarm partial <ID> --proof "commit:X tests:Y"`.
4.  **Inspection**: Wait for an inspector agent or human to run `swarm inspect <ID> --pass`.

## Code Standards

- **Python**: Follow PEP 8. Use type hints where possible.
- **Tests**: Add tests for all new features and bug fixes.
- **Markdown**: Keep `.swarm/*.md` files clean and follow the established schema.

## Governance

This project is currently maintained by Michael Lee (@MikeHLee). Major architectural decisions should be proposed as `SWC` items in `queue.md`.

### Conflict Resolution

If multiple agents/humans claim the same task, we use the `[COMPETING]` state. A supervisor agent or human operator will review the competing implementations and select the winner based on performance, test coverage, and code quality.

---

*“The swarm is the message.”*
