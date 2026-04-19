---
nav_exclude: true
---

# swarms.ai Integration — PR Guide (SWC-015)

**Target repo**: `github.com/kyegomez/swarms`
**Proposed location**: `swarms/integrations/dot_swarm/`
**Status**: Ready to open PR

---

## What This PR Adds

Three standalone classes (no mutual dependency — swarms.ai is optional for all three) that bridge dot_swarm's git-native stigmergic coordination with swarms.ai's agent orchestration:

| Class | Requires `pip install swarms`? | Purpose |
|---|---|---|
| `DotSwarmStateProvider` | No | Injects `.swarm/` state into any agent's system prompt |
| `DotSwarmWorkflow` | No (swarms.ai agents optional) | Executes `.swarm/workflows/*.md` definitions |
| `DotSwarmTool` | No | Structured tool interface for queue operations |
| `StigmergicSwarm` | Yes | Novel swarm architecture via indirect stigmergic coordination |

---

## Why It Belongs in swarms.ai

swarms.ai currently has **no built-in state persistence between runs**. Each swarm starts cold. dot_swarm fills this gap with a git-native, human-readable state layer that:

- Persists across sessions (`.swarm/queue.md`, `state.md`, `memory.md`)
- Is fully auditable via git history and `swarm audit`
- Can be edited by humans without any tooling
- Works with any LLM backend (Bedrock, Claude, Gemini, etc.)

The integration is additive — it doesn't change swarms.ai internals.

---

## Value Proposition

| swarms.ai Gap | dot_swarm Solution |
|---|---|
| No state persistence between runs | `.swarm/` markdown files survive restarts |
| No audit trail | `trail.log` + git history; `swarm audit --trail` |
| Agents can't see project context | `DotSwarmStateProvider.build_system_prompt()` |
| No structured work queue | `queue.md` with priority, claimed-by, depends |
| No workflow definitions | `.swarm/workflows/*.md` with `DotSwarmWorkflow` |
| Agents coordinate directly (tight coupling) | Stigmergic coordination: agents read/write shared state (loose coupling) |

---

## Usage Examples

### 1. Give any swarms.ai Agent project context

```python
from swarms import Agent
from dot_swarm.swarms_provider import DotSwarmStateProvider

provider = DotSwarmStateProvider(swarm_path="./.swarm")

agent = Agent(
    agent_name="Project-Coordinator",
    system_prompt=provider.build_system_prompt(agent_name="Project-Coordinator"),
    model_name="anthropic/claude-sonnet-4-5",
)

result = agent.run("What should I work on next?")
# Parse response and apply operations (claim/done/add) back to .swarm/
provider.apply_operations(result, agent_id="project-coordinator")
```

### 2. Run a markdown workflow with swarms.ai agents

```python
from swarms import Agent
from dot_swarm.swarms_provider import DotSwarmWorkflow

# Workflow defined in .swarm/workflows/oauth2.md:
#   step 1: swarm claim CLD-042  (agent: bedrock)
#   step 2: swarm claim CLD-043  (agent: claude)
#   step 3: swarm heal --fix

workflow = DotSwarmWorkflow.from_markdown(".swarm/workflows/oauth2.md")
workflow.add_agent("bedrock", bedrock_agent)
workflow.add_agent("claude", claude_agent)

result = workflow.run()
print(result["summary"])   # "3 ok, 0 failed, 0 skipped"
```

### 3. Give agents a structured tool to interact with the queue

```python
from swarms import Agent
from dot_swarm.swarms_provider import DotSwarmTool

tool = DotSwarmTool(swarm_path="./.swarm")

# Register as a callable tool in swarms.ai
agent = Agent(
    agent_name="Queue-Manager",
    tools=[tool],   # tool.__call__(operation, **kwargs)
    ...
)

# Agents call: tool(operation="claim", item_id="CLD-042", agent_id="agent-1")
# Agents call: tool(operation="status")
# Agents call: tool(operation="done", item_id="CLD-042", note="Merged PR #123")
```

### 4. StigmergicSwarm — novel coordination pattern

```python
from swarms import Agent
from dot_swarm.swarms_provider import StigmergicSwarm

# Agents coordinate indirectly through .swarm/ files —
# no direct message passing, no tight coupling.
swarm = StigmergicSwarm(
    swarm_path="./.swarm",
    agents=[researcher, analyst, implementer],
    max_rounds=10,
)

results = swarm.run("Implement OAuth2 integration")
# Each agent reads the queue, claims an item, works, marks done.
# Next agent sees updated state and claims the next item.
```

---

## Stigmergic Coordination vs. Direct Message Passing

swarms.ai agents today coordinate directly — Agent A sends output to Agent B. This creates tight coupling and requires online coordination.

The stigmergic model is different:

```
Direct (swarms.ai current):
  Agent A → message → Agent B → message → Agent C

Stigmergic (dot_swarm):
  Agent A → writes .swarm/queue.md
                          ↑
  Agent B reads queue ────┘ → writes done → Agent C reads queue
```

Benefits:
- **Asynchronous**: Agents don't need to be online simultaneously
- **Resilient**: If Agent B fails, Agent C can pick up the same item
- **Auditable**: Every state transition is a git-trackable file change
- **Human-in-the-loop**: Humans can inspect and edit `.swarm/` files at any time

This mirrors how social insects (ants, termites) coordinate construction without a central coordinator — they leave pheromone traces that other agents read and respond to.

---

## Proposed PR Structure

```
swarms/integrations/dot_swarm/
  __init__.py           # exports all four classes
  provider.py           # DotSwarmStateProvider
  workflow.py           # DotSwarmWorkflow
  tool.py               # DotSwarmTool
  stigmergic.py         # StigmergicSwarm
  README.md             # (this document, condensed)

tests/integrations/test_dot_swarm/
  test_provider.py      # standalone tests (no swarms dep)
  test_workflow.py      # standalone tests
  test_tool.py          # standalone tests
  test_stigmergic.py    # integration tests (requires swarms)
```

The source for these files already exists in `dot_swarm`:
- `src/dot_swarm/swarms_provider.py` — all four classes
- `tests/test_swarms_provider.py` — 33 standalone tests, all passing

---

## Relationship to swarms.ai Concepts

| swarms.ai | dot_swarm |
|---|---|
| `SequentialWorkflow` | `DotSwarmWorkflow` with `pattern: sequential` |
| `ConcurrentWorkflow` | `DotSwarmWorkflow` with `pattern: concurrent` |
| `MixtureOfAgents` | `DotSwarmWorkflow` with `pattern: mixture` |
| `AgentRearrange` | `swarm heal --fix` (realigns queue/state) |
| `SwarmRouter` | `swarm configure --via` (routes to LLM backends) |
| `SocialAlgorithms` | `StigmergicSwarm` (indirect coordination) |
| AOP (Agent Orchestration Protocol) | OGP-lite federation (`swarm federation`) |

---

## Dependency Notes

- `dot-swarm` adds no transitive dependencies to the swarms.ai install — only stdlib Python is used.
- `pip install dot-swarm` is the only required install for `DotSwarmStateProvider`, `DotSwarmWorkflow`, and `DotSwarmTool`.
- `StigmergicSwarm` imports `swarms` lazily; ImportError is raised with a helpful message if not installed.

---

## Test Coverage

```
tests/test_swarms_provider.py: 33 tests (all standalone, no swarms dep)
  - DotSwarmStateProvider: 11 tests
  - DotSwarmWorkflow: 12 tests
  - DotSwarmTool: 10 tests
```

All 195 dot_swarm tests pass (`PYTHONPATH=src python3 -m pytest tests/`).
