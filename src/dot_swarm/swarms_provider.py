"""dot_swarm × swarms.ai integration.

Provides four classes:

  DotSwarmStateProvider — standalone (no swarms.ai required)
      Reads .swarm/ state and injects it as structured context into any
      LLM agent's system prompt. Parses AI JSON responses and applies
      the resulting operations back to .swarm/ files.

  DotSwarmWorkflow — standalone (no swarms.ai required for basic use)
      Adapter that maps .swarm/workflows/*.md definitions to executable
      workflows. Optionally routes steps to swarms.ai Agents when
      add_agent() is called. Falls back to subprocess otherwise.

  DotSwarmTool — standalone (no swarms.ai required)
      Callable tool that exposes dot_swarm operations to any agent
      framework via a single structured JSON interface. Compatible with
      swarms.ai tool calling conventions.

  StigmergicSwarm — requires swarms.ai (lazy import)
      A novel swarm architecture where agents coordinate *indirectly*
      through shared .swarm/ state files rather than direct message
      passing. Each agent claims, works, and marks items done via the
      stigmergic protocol, enabling asynchronous, decentralised
      multi-agent workflows with a full git audit trail.

Usage (DotSwarmStateProvider — no deps beyond dot-swarm):
    from dot_swarm.swarms_provider import DotSwarmStateProvider

    provider = DotSwarmStateProvider(swarm_path="./.swarm")
    system_prompt = provider.build_system_prompt(agent_name="Coordinator")
    result_json = my_llm.complete(system_prompt, user_message)
    results = provider.apply_operations(result_json, agent_id="coordinator")

Usage (DotSwarmWorkflow):
    from dot_swarm.swarms_provider import DotSwarmWorkflow

    wf = DotSwarmWorkflow.from_markdown(".swarm/workflows/oauth2.md")
    result = wf.run(dry_run=True)      # preview steps
    result = wf.run()                  # execute via subprocess

    # With swarms.ai agents:
    wf.add_agent("bedrock", my_bedrock_agent)
    wf.add_agent("claude", my_claude_agent)
    result = wf.run()    # steps with matching agent: label call the agent

Usage (DotSwarmTool — any agent framework):
    from dot_swarm.swarms_provider import DotSwarmTool

    tool = DotSwarmTool(swarm_path="./.swarm")
    result = tool(operation="claim", item_id="CLD-042", agent_id="my-agent")
    result = tool(operation="status")     # returns queue summary

Usage (StigmergicSwarm — requires: pip install swarms):
    from dot_swarm.swarms_provider import StigmergicSwarm
    from swarms import Agent

    swarm = StigmergicSwarm(
        swarm_path="./.swarm",
        agents=[researcher, analyst, implementer],
    )
    swarm.run("Implement the OAuth2 integration")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# DotSwarmStateProvider
# ---------------------------------------------------------------------------

class DotSwarmStateProvider:
    """Reads .swarm/ state and exposes it for LLM agent injection.

    This class has zero external dependencies beyond dot-swarm itself.
    It is the recommended integration point for any agent framework.
    """

    def __init__(self, swarm_path: str | Path = ".") -> None:
        from .models import SwarmPaths
        p = Path(swarm_path)
        if p.name == ".swarm":
            self._paths = SwarmPaths.from_swarm_dir(p)
        else:
            found = SwarmPaths.find(p)
            if found is None:
                raise ValueError(
                    f"No .swarm/ directory found at or above {p}. "
                    "Run 'swarm init' first."
                )
            self._paths = found

    # --- Context building ---------------------------------------------------

    def build_context_bundle(self, token_limit: int = 1200) -> str:
        """Return a compact .swarm/ context string for prompt injection."""
        from .ai_ops import build_context_bundle
        return build_context_bundle(self._paths, context_limit=token_limit)

    def build_system_prompt(
        self,
        agent_name: str = "Agent",
        extra_instructions: str = "",
    ) -> str:
        """Build a full system prompt that injects .swarm/ state.

        The prompt instructs the agent to respect the stigmergic
        protocol: read the queue, claim items before working, mark
        done when complete, and log decisions to memory.
        """
        from .ai_ops import SYSTEM_PROMPT
        context = self.build_context_bundle()
        div_name = self._paths.root.parent.name

        header = (
            f"You are {agent_name}, an AI agent working inside the "
            f"dot_swarm coordination system for division '{div_name}'.\n\n"
            "STIGMERGIC PROTOCOL:\n"
            "1. Read the queue context below — claim an OPEN item before starting work.\n"
            "2. When you complete work, mark the item done with a note.\n"
            "3. Log non-obvious decisions to memory with a rationale.\n"
            "4. Do NOT claim items already CLAIMED by another agent.\n\n"
        )
        if extra_instructions:
            header += f"ADDITIONAL INSTRUCTIONS:\n{extra_instructions}\n\n"

        return header + SYSTEM_PROMPT + f"\n\n--- CURRENT STATE ---\n{context}"

    # --- Operation application ----------------------------------------------

    def apply_operations(
        self,
        response: str | dict,
        agent_id: str = "swarms-agent",
    ) -> list[str]:
        """Parse an AI JSON response and apply operations to .swarm/ files.

        Accepts either a raw JSON string or a pre-parsed dict.
        Returns a list of human-readable result strings.
        """
        from .ai_ops import execute_operations

        if isinstance(response, str):
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1]
            if clean.endswith("```"):
                clean = clean.rsplit("```", 1)[0]
            try:
                parsed = json.loads(clean.strip())
            except json.JSONDecodeError as e:
                return [f"  ✗ Could not parse AI response as JSON: {e}"]
        else:
            parsed = response

        ops = parsed.get("operations", [])
        write_ops = [o for o in ops if o.get("op") != "respond"]

        if not write_ops:
            commentary = parsed.get("commentary", "")
            respond_msgs = [o.get("message", "") for o in ops if o.get("op") == "respond"]
            return [commentary] + respond_msgs

        return execute_operations(self._paths, write_ops, agent_id)

    # --- Convenience accessors ----------------------------------------------

    def get_state(self) -> dict[str, str]:
        """Return parsed state.md as a dict."""
        from .operations import read_state
        return read_state(self._paths)

    def get_queue(self) -> dict[str, list]:
        """Return the queue as {'active': [...], 'pending': [...], 'done': [...]}."""
        from .operations import read_queue
        active, pending, done = read_queue(self._paths)
        return {
            "active": [{"id": i.id, "description": i.description, "priority": i.priority.value, "state": i.state.value} for i in active],
            "pending": [{"id": i.id, "description": i.description, "priority": i.priority.value} for i in pending],
            "done": [{"id": i.id, "description": i.description} for i in done[-10:]],
        }

    @property
    def division_name(self) -> str:
        return self._paths.root.parent.name


# ---------------------------------------------------------------------------
# DotSwarmWorkflow
# ---------------------------------------------------------------------------

class DotSwarmWorkflow:
    """Adapter mapping .swarm/workflows/*.md to executable multi-step workflows.

    Bridges dot_swarm's markdown-native workflow definitions with swarms.ai's
    orchestration patterns. Steps are executed via subprocess by default;
    steps with a matching `agent:` label are routed to registered swarms.ai
    Agents when available.

    This is the dot_swarm equivalent of swarms.ai SequentialWorkflow /
    ConcurrentWorkflow, expressed in human-readable markdown.
    """

    def __init__(self, workflow_file: str | Path) -> None:
        from .workflows import _parse_workflow_md, Workflow
        wf_path = Path(workflow_file)
        if not wf_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {wf_path}")
        self._path = wf_path
        self._wf: Workflow = _parse_workflow_md(
            wf_path.read_text(encoding="utf-8"),
            wf_path.stem,
        )
        self._agents: dict[str, Any] = {}

    @classmethod
    def from_markdown(cls, workflow_file: str | Path) -> "DotSwarmWorkflow":
        """Load a workflow from a markdown file path."""
        return cls(workflow_file)

    @classmethod
    def from_swarm_dir(cls, swarm_path: str | Path, name: str) -> "DotSwarmWorkflow":
        """Load a named workflow from a .swarm/ directory."""
        from .models import SwarmPaths
        p = Path(swarm_path)
        if p.name == ".swarm":
            paths = SwarmPaths.from_swarm_dir(p)
        else:
            found = SwarmPaths.find(p)
            if found is None:
                raise ValueError(f"No .swarm/ found at or above {p}")
            paths = found
        fname = name if name.endswith(".md") else f"{name}.md"
        return cls(paths.workflows / fname)

    @property
    def name(self) -> str:
        return self._wf.name

    @property
    def pattern(self) -> str:
        return self._wf.pattern

    @property
    def trigger(self) -> str:
        return self._wf.trigger

    @property
    def steps(self) -> list:
        return self._wf.steps

    def add_agent(self, label: str, agent: Any) -> "DotSwarmWorkflow":
        """Register a swarms.ai Agent for steps with matching agent: label.

        Args:
            label: The agent label used in workflow step `agent:` field
                   (e.g. "bedrock", "claude", "researcher").
            agent: A swarms.ai Agent (or any object with a .run(str) method).
        """
        self._agents[label] = agent
        return self

    def run(self, *, dry_run: bool = False, cwd: str | Path | None = None) -> dict[str, Any]:
        """Execute the workflow.

        Steps with a registered agent label call agent.run(command).
        All other steps are executed as subprocess shell commands.

        Returns a dict with: ok (bool), summary (str), steps (list of step results).
        """
        from .workflows import WorkflowStep, StepResult, WorkflowRun, _eval_condition, _now

        results: list[StepResult] = []
        context: dict[str, StepResult] = {}
        work_dir = str(cwd or self._path.parent.parent)

        for step in self._wf.steps:
            key = f"step{step.number}"

            if step.condition and not _eval_condition(step.condition, context):
                sr = StepResult(
                    step_number=step.number, command=step.command,
                    exit_code=0, stdout="", stderr="",
                    ran_at=_now(), skipped=True,
                    skip_reason=f"condition '{step.condition}' not met",
                )
                results.append(sr)
                context[key] = sr
                continue

            sr = self._exec_step(step, work_dir, dry_run)
            results.append(sr)
            context[key] = sr

            if not sr.ok and not dry_run:
                for remaining in self._wf.steps[self._wf.steps.index(step) + 1:]:
                    results.append(StepResult(
                        step_number=remaining.number,
                        command=remaining.command,
                        exit_code=0, stdout="", stderr="",
                        ran_at=_now(), skipped=True,
                        skip_reason=f"step {step.number} failed",
                    ))
                break

        ok = all(r.ok or r.skipped for r in results)
        n_ok = sum(1 for r in results if r.ok)
        n_fail = sum(1 for r in results if not r.ok and not r.skipped)
        n_skip = sum(1 for r in results if r.skipped)
        summary = f"{n_ok} ok, {n_fail} failed, {n_skip} skipped"

        return {
            "workflow": self.name,
            "pattern": self.pattern,
            "ok": ok,
            "summary": summary,
            "steps": [
                {
                    "n": r.step_number,
                    "command": r.command,
                    "ok": r.ok,
                    "skipped": r.skipped,
                    "skip_reason": r.skip_reason,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "exit_code": r.exit_code,
                }
                for r in results
            ],
        }

    def _exec_step(self, step: Any, cwd: str, dry_run: bool) -> Any:
        from .workflows import StepResult, _now
        import subprocess

        if dry_run:
            return StepResult(
                step_number=step.number, command=step.command,
                exit_code=0, stdout=f"[dry-run] would run: {step.command}",
                stderr="", ran_at=_now(),
            )

        agent = self._agents.get(step.agent)
        if agent is not None:
            try:
                response = agent.run(step.command)
                return StepResult(
                    step_number=step.number, command=step.command,
                    exit_code=0,
                    stdout=str(response)[:500] if response else "",
                    stderr="", ran_at=_now(),
                )
            except Exception as exc:
                return StepResult(
                    step_number=step.number, command=step.command,
                    exit_code=1, stdout="", stderr=str(exc), ran_at=_now(),
                )

        try:
            result = subprocess.run(
                step.command, shell=True, capture_output=True, text=True,
                timeout=step.timeout_min * 60, cwd=cwd,
            )
            return StepResult(
                step_number=step.number, command=step.command,
                exit_code=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                ran_at=_now(),
            )
        except subprocess.TimeoutExpired:
            return StepResult(
                step_number=step.number, command=step.command,
                exit_code=124, stdout="",
                stderr=f"timeout after {step.timeout_min}m", ran_at=_now(),
            )
        except Exception as exc:
            return StepResult(
                step_number=step.number, command=step.command,
                exit_code=1, stdout="", stderr=str(exc), ran_at=_now(),
            )


# ---------------------------------------------------------------------------
# DotSwarmTool
# ---------------------------------------------------------------------------

class DotSwarmTool:
    """Structured tool interface for dot_swarm operations.

    Exposes dot_swarm queue operations as a single callable compatible with
    swarms.ai tool-calling conventions. Agents call this tool with a JSON
    operation spec to read/write .swarm/ state.

    Supported operations:
        status          — Return queue summary as a string
        claim           — Claim an OPEN item (requires item_id, agent_id)
        done            — Mark a claimed item done (requires item_id, agent_id)
        add             — Add a new work item (requires description; optional: priority, project)
        memory          — Append a memory entry (requires topic, decision, why)
        heal            — Run alignment check and return findings

    Returns a dict with: ok (bool), message (str), data (optional dict).
    """

    name: str = "dot_swarm"
    description: str = (
        "Read and write .swarm/ project state. Use 'status' to see the queue, "
        "'claim' to take a work item, 'done' to mark it complete, 'add' to create "
        "a new item, 'memory' to log a decision, and 'heal' to check alignment."
    )

    def __init__(self, swarm_path: str | Path = ".") -> None:
        self._provider = DotSwarmStateProvider(swarm_path)

    def __call__(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a dot_swarm operation.

        Args:
            operation: One of 'status', 'claim', 'done', 'add', 'memory', 'heal'.
            **kwargs: Operation-specific arguments (see class docstring).

        Returns:
            dict with keys: ok (bool), message (str), data (optional dict).
        """
        handler = getattr(self, f"_op_{operation}", None)
        if handler is None:
            return {
                "ok": False,
                "message": f"Unknown operation '{operation}'. "
                           f"Valid: status, claim, done, add, memory, heal",
            }
        try:
            return handler(**kwargs)
        except Exception as exc:
            return {"ok": False, "message": f"Operation '{operation}' failed: {exc}"}

    def _op_status(self, **_: Any) -> dict[str, Any]:
        queue = self._provider.get_queue()
        active = queue["active"]
        pending = queue["pending"]
        lines = [f"Active ({len(active)}): " + ", ".join(i["id"] for i in active) if active else "Active: (none)"]
        lines.append(f"Pending ({len(pending)}): " + ", ".join(i["id"] for i in pending[:5]) +
                     ("..." if len(pending) > 5 else "") if pending else "Pending: (none)")
        return {"ok": True, "message": "\n".join(lines), "data": queue}

    def _op_claim(self, item_id: str, agent_id: str = "swarms-agent", **_: Any) -> dict[str, Any]:
        results = self._provider.apply_operations(
            {"operations": [{"op": "claim", "id": item_id, "agent": agent_id}]},
            agent_id=agent_id,
        )
        ok = any("✓" in r or "claimed" in r.lower() for r in results)
        return {"ok": ok, "message": "\n".join(results)}

    def _op_done(self, item_id: str, agent_id: str = "swarms-agent",
                 note: str = "", **_: Any) -> dict[str, Any]:
        op: dict[str, Any] = {"op": "done", "id": item_id, "agent": agent_id}
        if note:
            op["note"] = note
        results = self._provider.apply_operations({"operations": [op]}, agent_id=agent_id)
        ok = any("✓" in r or "done" in r.lower() for r in results)
        return {"ok": ok, "message": "\n".join(results)}

    def _op_add(self, description: str, priority: str = "medium",
                project: str = "misc", agent_id: str = "swarms-agent", **_: Any) -> dict[str, Any]:
        op = {"op": "add", "description": description,
              "priority": priority, "project": project}
        results = self._provider.apply_operations({"operations": [op]}, agent_id=agent_id)
        ok = any("✓" in r or "added" in r.lower() for r in results)
        return {"ok": ok, "message": "\n".join(results)}

    def _op_memory(self, topic: str, decision: str, why: str,
                   agent_id: str = "swarms-agent", **_: Any) -> dict[str, Any]:
        op = {"op": "memory", "topic": topic, "decision": decision, "why": why}
        results = self._provider.apply_operations({"operations": [op]}, agent_id=agent_id)
        ok = any("✓" in r or "memory" in r.lower() for r in results)
        return {"ok": ok, "message": "\n".join(results)}

    def _op_heal(self, **_: Any) -> dict[str, Any]:
        from .security import scan_swarm_directory, format_findings
        from .signing import verify_trail
        paths = self._provider._paths
        findings = scan_swarm_directory(paths)
        trail_failures = verify_trail(paths.root)
        trail_ok = len(trail_failures) == 0
        trail_msg = "OK" if trail_ok else f"{len(trail_failures)} invalid signature(s)"
        lines = [f"Security scan: {len(findings)} finding(s)"]
        if findings:
            lines.append(format_findings(findings)[:400])
        lines.append(f"Trail: {trail_msg}")
        return {
            "ok": len(findings) == 0 and trail_ok,
            "message": "\n".join(lines),
            "data": {
                "finding_count": len(findings),
                "trail_ok": trail_ok,
            },
        }


# ---------------------------------------------------------------------------
# StigmergicSwarm
# ---------------------------------------------------------------------------

class StigmergicSwarm:
    """Multi-agent swarm coordinated through .swarm/ stigmergic state.

    Agents communicate indirectly by reading and writing .swarm/ markdown
    files rather than passing messages directly. This enables:
    - Asynchronous, decentralised coordination
    - Full git audit trail of every agent action
    - Human-in-the-loop: any file is readable and editable
    - Graceful handling of agent failures (work stays in queue)

    Requires: pip install swarms

    Architecture:
      1. Task is broadcast to all agents as context
      2. Each agent independently reads the queue and claims an OPEN item
      3. Agent works on its claimed item and marks it done
      4. Other agents see the updated state and claim next items
      5. Continues until queue is empty or max_rounds reached

    Example:
        from swarms import Agent
        from dot_swarm.swarms_provider import StigmergicSwarm

        swarm = StigmergicSwarm(
            swarm_path="./.swarm",
            agents=[researcher, analyst, implementer],
            max_rounds=10,
        )
        results = swarm.run("Implement the OAuth2 integration")
    """

    def __init__(
        self,
        swarm_path: str | Path = ".",
        agents: list[Any] | None = None,
        max_rounds: int = 10,
        verbose: bool = True,
    ) -> None:
        self.provider = DotSwarmStateProvider(swarm_path)
        self.agents = agents or []
        self.max_rounds = max_rounds
        self.verbose = verbose
        self._results: list[dict] = []

    def add_agent(self, agent: Any) -> "StigmergicSwarm":
        """Add an agent to the swarm (fluent interface)."""
        self.agents.append(agent)
        return self

    def run(self, task: str) -> dict[str, Any]:
        """Run the swarm on *task* using stigmergic coordination.

        Each agent is given the current .swarm/ context and asked to
        claim and complete one work item per round. The swarm continues
        until the queue is empty or max_rounds is reached.

        Returns a summary dict with agent outputs and final queue state.
        """
        try:
            from swarms import Agent  # type: ignore[import]
        except ImportError as e:
            raise ImportError(
                "StigmergicSwarm requires swarms. "
                "Install with: pip install swarms"
            ) from e

        if not self.agents:
            raise ValueError("No agents added. Use StigmergicSwarm.add_agent() or pass agents= at init.")

        if self.verbose:
            print(f"\n🐝 StigmergicSwarm starting — {len(self.agents)} agent(s), max {self.max_rounds} rounds")
            print(f"   Division: {self.provider.division_name}")
            print(f"   Task: {task}\n")

        round_results: list[dict] = []

        for round_num in range(1, self.max_rounds + 1):
            queue = self.provider.get_queue()
            pending_count = len(queue["pending"])
            active_count = len(queue["active"])

            if pending_count == 0 and active_count == 0:
                if self.verbose:
                    print(f"  ✓ Queue empty after {round_num - 1} round(s). Swarm complete.")
                break

            if self.verbose:
                print(f"  Round {round_num}: {active_count} active, {pending_count} pending")

            round_output: dict = {"round": round_num, "agent_results": []}

            for agent in self.agents:
                system_prompt = self.provider.build_system_prompt(
                    agent_name=getattr(agent, "agent_name", "Agent"),
                    extra_instructions=f"Original task: {task}",
                )

                instruction = (
                    f"Review the current .swarm/ state above. "
                    f"Claim one OPEN work item related to: {task}. "
                    f"Complete it and mark it done. "
                    f"If no relevant item exists, respond explaining why."
                )

                try:
                    response = agent.run(instruction, system_prompt=system_prompt)
                    op_results = self.provider.apply_operations(
                        response,
                        agent_id=getattr(agent, "agent_name", f"agent-{id(agent)}"),
                    )
                    round_output["agent_results"].append({
                        "agent": getattr(agent, "agent_name", str(agent)),
                        "response": response[:200] if isinstance(response, str) else str(response)[:200],
                        "operations": op_results,
                    })
                    if self.verbose:
                        for r in op_results:
                            print(f"    [{getattr(agent, 'agent_name', 'agent')}] {r}")
                except Exception as e:
                    round_output["agent_results"].append({
                        "agent": getattr(agent, "agent_name", str(agent)),
                        "error": str(e),
                    })
                    if self.verbose:
                        print(f"    ⚠ {getattr(agent, 'agent_name', 'agent')}: {e}")

            round_results.append(round_output)

        final_queue = self.provider.get_queue()
        summary = {
            "division": self.provider.division_name,
            "task": task,
            "rounds_completed": len(round_results),
            "round_results": round_results,
            "final_queue": final_queue,
            "final_state": self.provider.get_state(),
        }

        if self.verbose:
            done_count = len(final_queue["done"])
            pending_count = len(final_queue["pending"])
            print(f"\n  Summary: {done_count} items done, {pending_count} remaining")

        return summary
