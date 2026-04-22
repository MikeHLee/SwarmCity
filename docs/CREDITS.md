---
title: Credits
nav_order: 7
---

# Credits & Inspirations

dot_swarm stands on the shoulders of decades of research into how complex,
coordinated behavior emerges from simple local interactions — no central
command required.

---

## Primary Inspiration

### Steve Yegge — "Welcome to Gas Town"

> *"I'm running 20-30 Claude Code agents simultaneously, every day…
> The trick is nondeterministic idempotence."*

Steve Yegge's January 2026 essay
["Welcome to Gas Town"](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04)
is the direct inspiration for dot_swarm's design philosophy. The essay
describes coordinating large fleets of Claude Code agents across a real
software organization — naming the challenge of making agent work
**idempotent under nondeterminism**, and introducing the notion of
**MEOW (Molecular Expression of Work)** as the unit of agent-driven
progress.

dot_swarm's `.swarm/` directory, `queue.md` lifecycle, and item-ID
convention are a direct implementation of the patterns Yegge describes:
small, claimable units of work that agents can pick up, checkpoint, and
hand off without stepping on each other.

---

## The Biological Argument

Central coordination is expensive. In the natural systems that inspired dot_swarm,
it is avoided almost universally — and in the rare cases where a "central" figure
exists, the burden of coordination is not placed on that figure at all.

An ant or bee queen does not manage work. She does not assign tasks, resolve
conflicts, or approve sub-team formation. She emits **chemical markers** —
pheromone signals that encode colony state — and workers read those signals
autonomously to decide what to do. The queen's energy budget is not consumed by
coordination overhead. Coordination is a property of the **shared medium**, not of
any single agent.

This design produces emergent capabilities no top-down architecture could replicate
at the same cost:

- **Hive splitting** — when a colony grows beyond a threshold, a subset self-organises
  around a new queen without any central directive. Multi-master by default.
- **Task-oriented sub-teams** — foraging, defence, nursing, and construction teams
  form and dissolve based on pheromone gradient signals, not management assignments.
- **Fault tolerance** — loss of any individual, including the queen, does not
  immediately collapse coordination. The medium persists; workers re-orient.

The single prerequisite for all of this: **all members speak the same chemical
language.** Pheromone signals only work if every worker interprets them the same way.
The protocol is the coordination.

dot_swarm is a direct translation of this principle to software agent fleets. Models
and tools that modify filesystem-native projects are better off leaving traces in their
environment — readable by any subsequent agent — than reporting state to a central node
around which complicated systems must be arranged to prevent bottlenecks and data loss
from information overload. As long as agents speak the same language (follow
`BOOTSTRAP.md`), coordination emerges from the files themselves.

---

## Scientific Foundations

### Stigmergy — Indirect Coordination via Environment

The `.swarm/state.md` "pheromone trail" pattern — where agents read
and update shared environment state rather than communicating directly —
is an instance of **stigmergy**, first described by French entomologist
Pierre-Paul Grassé studying termite mound construction.

#### Foundational Papers

**1. The original concept**

> Grassé, P.-P. (1959). La reconstruction du nid et les coordinations
> interindividuelles chez *Bellicositermes natalensis* et *Cubitermes* sp.
> La théorie de la stigmergie: Essai d'interprétation du comportement des
> termites constructeurs. *Insectes Sociaux*, 6(1), 41–81.

Grassé coined "stigmergy" (*stigma* = mark, *ergon* = work) to explain
how termites build kilometre-scale mounds without a blueprint or
foreman — each worker responds to traces left in the structure itself.
**Key insight**: coordination arises from the environment, not from
inter-agent messaging.

---

**2. The bridge to artificial systems**

> Theraulaz, G., & Bonabeau, E. (1999). A brief history of stigmergy.
> *Artificial Life*, 5(2), 97–116.

Traces stigmergy from Grassé's termites through 40 years of ethology
and into distributed AI, showing how the concept generalises from
insects to any system where agents modify a shared medium and respond
to those modifications.

---

**3. The textbook**

> Bonabeau, E., Dorigo, M., & Theraulaz, G. (1999).
> *Swarm Intelligence: From Natural to Artificial Systems*.
> Oxford University Press.

The definitive reference for swarm intelligence. Covers self-organisation,
stigmergy, emergent problem solving, and their engineering applications.
dot_swarm's multi-division "colony" model maps directly to the
decentralised swarms described here.

---

**4. Ant Colony Optimisation**

> Dorigo, M., Maniezzo, V., & Colorni, A. (1996). Ant System:
> Optimization by a colony of cooperating agents.
> *IEEE Transactions on Systems, Man, and Cybernetics — Part B*,
> 26(1), 29–41.

The paper that showed ant pheromone trails could solve NP-hard routing
problems. Directly inspired dot_swarm's priority-weighted queue: items
claimed often accumulate implicit "pheromone weight" through repeated
attention.

---

**5. Stigmergy in engineering**

> Parunak, H. V. D. (1997). "Go to the ant": Engineering principles
> from natural agent systems. *Annals of Operations Research*, 75, 69–101.

One of the first papers to formally bridge stigmergy and software
engineering, arguing that ants demonstrate scalable, fault-tolerant
coordination principles directly applicable to distributed software
systems. dot_swarm's `.swarm/` shared-file model is a filesystem
implementation of precisely this principle.

---

## Nature Collection

The [Nature collection on Collective Behaviour in Animals](https://www.nature.com/collections/cgbgjbahac)
gathers modern research on how signal trails, pheromone gradients, and
local interaction rules produce colony-level intelligence — the same
phenomena dot_swarm adapts for software agent fleets.

---

## Protocol Engineering & Federated Coordination

### OGP — Open Gateway Protocol

> Proctor, D. (2026). "Case Study: Building a Protocol in the Age of AI."
> *Trilogy AI Substack*.
> https://trilogyai.substack.com/p/case-study-building-a-protocol-in

David Proctor's public post-mortem on building OGP — a federated inter-agent
protocol — is one of the most concrete accounts of what goes wrong when
**identity, trust, and persistence assumptions are made incorrectly** in a
multi-agent system.

Two threads from this work are directly foundational to dot_swarm:

**1. Inter-agent identity and trust**

OGP's early design treated identity as a hostname:port pair — a mutable,
network-layer address rather than a cryptographic fingerprint. This produced
a class of bugs where peer identity silently shifted across restarts or
network changes. The lesson, applied in `federation.py`:

> *"Identity is a fingerprint, never an address."*

dot_swarm's `doorman_check()` always resolves `from_fingerprint` from the
stored `trusted_peers/` record — it never trusts the identity claimed in
the message body itself. This is a direct application of the OGP post-mortem.

**2. Security under adversarial conditions**

The post-mortem surfaces a category of failure that is easy to miss when
building in good faith: **an attacker who controls the message body can
impersonate any peer if the receiver trusts the sender's own claim**. This
applies not only to federation but to any system that ingests external text —
including LLM prompt contexts.

This insight directly motivated dot_swarm's `security.py` adversarial scanner:
the same trust-the-claim failure mode that breaks cross-agent federation also
enables prompt injection attacks (an adversarial "agent" claims authority it
was not granted). The 18-pattern scanner, the three-layer doorman model, and
the signed pheromone trail all address variants of this same root problem.

**Relationship to dot_swarm's design:**

| OGP lesson | dot_swarm implementation |
|---|---|
| Identity = fingerprint, not address | `identity.json` stores `fingerprint`; `trust_peer()` indexes on it |
| Persist before returning success | `trust_peer()` calls `_atomic_write()` before `return` |
| Never trust claimed sender ID | `doorman_check()` looks up stored record — ignores `from_fingerprint` field in message |
| Layered scopes limit blast radius | `policy.md` → `trusted_peers/<fp>.json` → runtime `doorman_check()` |
| HMAC is wrong for cross-party signing | HMAC retained for local trail only; Ed25519 documented as upgrade path |

---

## Design Lineage

| Biological concept | dot_swarm implementation |
|---|---|
| Termite pheromone deposit | `state.md` **Current focus** / **Blockers** |
| Ant trail reinforcement | Item priority + reclaim count |
| Nest-site recruitment | `swarm explore` / `swarm report` heartbeat |
| Division of labour | Per-division `.swarm/` isolation |
| Colony memory | `memory.md` append-only log |
| Handoff signal | `swarm handoff` structured note |

---

*If you have built something with dot_swarm, we'd love to hear about it.
Open an issue or start a discussion on [GitHub](https://github.com/MikeHLee/dot_swarm).*
