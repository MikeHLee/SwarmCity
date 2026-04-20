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

---

## 2026-04-19 — swarms.ai integration: transport-agnostic, additive only (human-ML + claude-sonnet-4-6)

**Decision**: The swarms.ai integration (SWC-015) adds four standalone classes to
`swarms/integrations/dot_swarm/` with no changes to swarms.ai internals. None of the
four classes require `pip install swarms` to function — the dependency is entirely optional.

**Why**: swarms.ai has no built-in state persistence between runs. dot_swarm fills this
gap non-invasively. Making the integration one-directional (dot_swarm → swarms.ai, not the
reverse) keeps the two projects decoupled and makes the PR easier to review and accept.

**Classes**: `DotSwarmStateProvider` (system prompt injection), `DotSwarmWorkflow`
(runs `.swarm/workflows/*.md`), `DotSwarmTool` (queue operation interface),
`StigmergicSwarm` (novel indirect-coordination swarm architecture).

**PR not yet opened** — waiting for v0.3.0 PyPI publication (SWC-004) to reference a
stable package version in the PR description.

---

## 2026-04-19 — trail invisible by default; docs internal notes removed from repo (human-ML + claude-sonnet-4-6)

**Decision**: `swarm init` now defaults to invisible (adds `.swarm/` to `.gitignore`).
Internal integration and platform docs (SWARMS_AI_PR_GUIDE.md, INTEGRATION_PLAN.md,
PLATFORM_SETUP.md) removed from `docs/` — content summarised into this memory file
and into queue.md notes for their respective items.

**Why**: Sharing a repo was silently sharing the full swarm trail (every claim, handoff,
decision entry). This violates the principle that sharing code should be a separate
decision from sharing coordination history. The `swarm trail visible/invisible` commands
(SWC-026) make this explicit and reversible.

**Tradeoff**: First-time users won't see the trail in git by default. They will see a
"Trail: hidden" note in `swarm init` output directing them to `swarm trail visible`.

---

## 2026-04-19 — docs migrated from MkDocs to Jekyll/just-the-docs; oasis-x color scheme (human-ML + claude-sonnet-4-6)

**Decision**: Switch from MkDocs Material to just-the-docs (Jekyll). Color scheme pulled
live from dev.o-x.io: #fafafa background, #165f59 teal accent, #009b5c green secondary,
Montserrat font. Deploy via `peaceiris/actions-gh-pages@v4` to gh-pages branch (no
GitHub Pages source setting change required).

**Why**: MkDocs Material uses Python and pip in CI; Jekyll is GitHub Pages native and
requires no separate deploy dependency. just-the-docs is the cleanest docs-focused Jekyll
theme. The oasis-x aesthetic (minimal, white, teal) is more consistent with the project
brand than MkDocs Material's dark purple defaults.

**MkDocs-specific syntax converted**: `!!! note/warning/quote` admonitions →
`{: .note }` / `{: .warning }` callouts; `=== "Tab"` sections → plain H4 headings.
