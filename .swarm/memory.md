# Memory — dot_swarm

Append-only. Non-obvious decisions, constraints, and rationale.
Format: `## <ISO8601-date> — <topic> (<agent-id>)`

---

## 2026-04-03 — Research strategy: two separate papers, not one (human-ML + agent)

**Decision**: Pursue two separate papers rather than a single combined submission.

**Why**: The stigmergy contribution (dot_swarm orchestration protocol) and the Boids looping
contribution (gen_logo.py physics pipeline) have entirely different audiences, venues, and
evaluation requirements. Bundling them would weaken both: AAMAS reviewers don't care about
GIF loop fidelity; SIGGRAPH Talks reviewers don't care about multi-agent file locking.

**Stigmergy paper (SWC-007)** → AAMAS 2027 or LLM-agents workshop (NeurIPS/ICLR 2026-27).
Key gap to fill: need a quantitative evaluation (coordination latency vs GitHub Issues/Jira,
drift detection F1) and at least one case study of a real multi-agent run.

**Boids looping paper (SWC-008)** → SIGGRAPH 2027 Talks (preferred) or Eurographics 2027 short.
Key gap: ablation study removing each constraint (jerk-only, snap-only, no Hermite, no
trajectory capture) and measuring loop error + a perceptual score. The loop error metric
(2.10 → 0.0057) is already a strong hook; ablation makes it a complete argument.

**Tradeoff**: Two papers means twice the writing overhead. Mitigated by the fact that the
BoidRunner blog post (SWC-009 Phase 1) doubles as a draft for the Boids paper's intro/results
section — write the blog post first, then expand into a paper.

---

## 2026-04-03 — BoidRunner: blog-first, no premature package (human-ML + agent)

**Decision**: Do not publish BoidRunner to PyPI until the blog post has validated the API design
with real readers.

**Why**: gen_logo.py is tightly coupled to the dot_swarm logo use case (hex backgrounds,
specific canvas sizes, GIF output). Extracting a clean `Swarm` class requires a day of
refactoring and forces API decisions (normalized units? callback hooks? renderer abstraction?)
that are easier to make after seeing what readers actually want to do with it.

**Tradeoff**: Delays the package. Accepted — a blog post with GIFs on Hacker News will drive
more awareness and better API feedback than a PyPI package with no documentation landing page.

**Browser simulator / game (Phase 3)**: Deferred until Phase 2 package exists and has traction.
JS port preferred over Pyodide/WASM for zero load-time and mobile support. Could evolve into
a casual game where users race to minimize loop error by tuning boid parameters.
