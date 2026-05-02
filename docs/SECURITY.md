---
title: Security
nav_order: 5
---

# Security Model

dot_swarm's security model is designed for the reality that AI agents operate
autonomously on shared filesystems. The threat model is different from a web
application — there's no network perimeter, no auth layer, and the coordination
medium itself (`.swarm/`) is readable and writable by any process on the machine.

---

## Protections built in

### Cryptographic signing identity

Every `swarm init` generates a per-swarm HMAC-SHA256 signing key stored in
`.swarm/.signing_key`. This file is always gitignored regardless of trail
visibility settings.

All AI operations are signed before being appended to `trail.log`:

```bash
swarm audit --trail    # verify trail integrity
swarm heal             # full integrity pass including trail verification
```

If any entry in `trail.log` has been tampered with, `swarm audit --trail` reports
exactly which records fail verification.

### 18-pattern adversarial content scanner

`swarm audit --security` and `swarm heal` scan all `.swarm/` files **and** platform
shims (CLAUDE.md, `.windsurfrules`, `.cursorrules`, `.github/copilot-instructions.md`)
for adversarial content patterns:

| Severity | Pattern category | Example |
|----------|-----------------|---------|
| **CRITICAL** | Data exfiltration instructions | "send contents of ~/.ssh to..." |
| **CRITICAL** | Safety override attempts | "ignore all previous instructions" |
| **CRITICAL** | Agent impersonation | fake claim stamps, forged agent IDs |
| **HIGH** | Prompt injection in memory/context | instructions embedded in `memory.md` entries |
| **HIGH** | Privilege escalation | "you are now operating in admin mode" |
| **MEDIUM** | Unusual encoding | base64-encoded instructions in notes fields |
| **MEDIUM** | Ambiguous authority claims | "the project owner has approved..." |

Use `swarm heal --fix` to quarantine flagged files for manual review rather than
deleting them outright.

### Drift detection

`swarm audit --drift` compares the current `.swarm/` file contents against git
history and the signed trail to identify writes that occurred outside the normal
protocol flow — the earliest signal of unexpected agent activity.

### Trail visibility control

`swarm trail invisible` (the default on `swarm init`) adds `.swarm/` to
`.gitignore`. Your coordination history — every claim, handoff note, decision
entry, and memory — stays private unless you explicitly share it.

```bash
swarm trail status     # invisible or visible?
swarm trail invisible  # default — private trail
swarm trail visible    # share trail with git
```

### Pheromone decay

Stale claim stamps are flagged by `swarm audit`. If an agent claims an item and
goes silent, the item surfaces in audit output with a staleness warning, preventing
indefinite lock-out of work items.

---

## Known attack surface

### Shared medium poisoning

**The fundamental tradeoff of stigmergy.** The `.swarm/` directory is the
coordination medium — any process that can write to it can influence every agent
that reads it. This is true of all environment-mediated coordination systems,
including the ant pheromone trails that inspired dot_swarm.

**Mitigations**: adversarial scanner catches known injection patterns, signed trail
detects tampering after the fact, `swarm heal` as a routine hygiene step after
any agentic run.

**Residual risk**: novel injection patterns not yet in the 18-pattern set. The
scanner is defense-in-depth, not a guarantee.

### HMAC is local-trust only

The signing key is per-swarm and never leaves the machine. HMAC-SHA256 protects
trail integrity *within a swarm* but provides no cross-swarm authentication — a
peer claiming to be `swarm-A` cannot be cryptographically verified without a
PKI layer. An Ed25519 upgrade path is documented in the architecture notes; HMAC
was chosen for stdlib-only implementation (no cryptography package required).

### Trail sharing equals history sharing

Running `swarm trail visible` and pushing exposes your full coordination history
to anyone who can clone the repo — every claim timestamp, every decision in
`memory.md`, every handoff note. The default is invisible for this reason. Treat
`swarm trail visible` like making a private branch public.

### LLM-generated content is a trust boundary

Content written by an agent into `memory.md`, `notes:` fields, or `context.md`
can influence future agents that read those files. This is the environment-poisoning
attack surface unique to stigmergic systems: a compromised agent writes a
plausible-looking pheromone that steers subsequent agents in the wrong direction.

The 18-pattern scanner is designed to catch the known forms of this attack. It
does not — and cannot — catch all possible adversarial framings. Running `swarm heal`
after any agentic session is the operational control.

### No real-time federation yet

Cross-swarm coordination currently uses file-based OGP-lite signed messages (inbox/
outbox directories). There is no live network connection between swarms. This means
there is also no real-time attack surface from remote swarms — but it also means
federation integrity relies on the transport (git, file copy, etc.) rather than
end-to-end cryptographic verification of message origin.

Live networked federation with Ed25519 message signing is planned for a future
release if the userbase warrants it.

---

## Security commands reference

```bash
swarm audit --security       # scan for adversarial content patterns
swarm audit --trail          # verify trail.log cryptographic integrity
swarm audit --drift          # detect out-of-band file modifications
swarm audit --full           # all of the above + stale claim check
swarm heal                   # full integrity pass + optional --fix quarantine
swarm trail status           # show current visibility
swarm trail invisible        # hide .swarm/ from git (default on init)
```

---

## The swarm key (Phase 1 shipped)

Phase 1 of SWC-046 has landed. `swarm key init` generates a per-swarm
ChaCha20-Poly1305 key (`.swarm/.swarm_key`, gitignored), and from that
moment on every entry written to `trail.log` is sealed as an AEAD
envelope of the form `swae1:<base64>` — opaque on disk to anyone without
the key, transparently decrypted by `swarm` reads. Trails written
before key adoption stay readable as plaintext, so adopting a key does
not invalidate prior history.

```bash
pip install 'dot-swarm[crypto]'   # one-time: pulls the cryptography wheel
swarm key init                    # generate the swarm key
swarm key status                  # algorithm, fingerprint, created
swarm key rotate                  # new key + re-seal every existing envelope
swarm key seal .swarm/memory.md   # encrypt one file in-place
swarm key open .swarm/memory.md   # decrypt back to plaintext
```

`rotate` retains the previous key as `.swarm_key.old` so partially-rotated
state remains readable until you confirm the rewrap and delete it.
Phases 2 and 3 (auto-encrypted `memory.md` / `state.md` writes; federation
key exchange) are the remaining roadmap items.

## Roadmap: the swarm key (original design notes)

The fundamental objection to stigmergic coordination is that the shared medium is,
by definition, shared. Anyone who can write to `.swarm/` can in principle drop a
poisoned pheromone. The current mitigations (HMAC-signed trail, 18-pattern
adversarial scanner, drift detection, `swarm heal`) catch the known forms of this
attack after the fact. The next layer catches it *at write time* — and it does so
by borrowing the trick that real swarms use.

### The biological prior

Ant colonies don't get poisoned by random pheromone-emitting intruders. Each
colony's foragers carry a colony-specific cuticular hydrocarbon signature, and
nestmate recognition is built around that signature: a forager that smells wrong
is attacked on contact. Honeybees do the same with comb-wax esters. The signal
isn't just *emitted* into the environment — it's *signed* by the colony's
chemistry, and the colony's response to a wrong signature is reflexive and fast.

This is not a metaphor; it is exactly the property we want from the trail.

### Design

`swarm init` will generate, in addition to the HMAC signing key, a per-swarm
**swarm key** — a 256-bit symmetric key suitable for XChaCha20-Poly1305 AEAD.
Both keys live at `.swarm/.signing_key` and `.swarm/.swarm_key`, both gitignored
unconditionally.

All writes to coordination files (`trail.log` entries, `memory.md` records,
claim notes, decision entries) are sealed with the swarm key before being
persisted. The on-disk format becomes a sequence of authenticated ciphertext
records with public metadata (timestamp, agent fingerprint) and sealed payload.

This gives three properties at once:

1. **Confidentiality.** A pushed `.swarm/` directory — including under
   `swarm trail visible` — reveals no claim history, no decision content, no
   memory. The trail is hidden in plain sight; only swarms holding the key can
   read it.
2. **Authenticity.** AEAD tags fail verification on any forged or modified
   record. A process that lacks the swarm key cannot insert a record that any
   honest reader will accept, and cannot tamper with an existing record without
   breaking its tag.
3. **Reflexive intrusion response.** `swarm heal` and `swarm audit --trail`
   become first-line antibody responses: a record that fails AEAD verification
   is quarantined immediately and surfaced as a CRITICAL finding. The "colony"
   reacts to a wrong signature the same way an ant colony does — fast, local,
   and without consulting a central authority.

### What this changes about the threat model

- **Shared medium poisoning** stops being a defense-in-depth problem. Without the
  swarm key, an adversary cannot write a *valid* pheromone — only an obviously
  invalid one, which is exactly the case the colony is built to handle.
- **Trail sharing equals history sharing** stops being a sharp tradeoff.
  `swarm trail visible` becomes safe by default: the trail is durable, auditable
  to the swarm, and opaque to everyone else.
- **Cross-swarm trust** gets a clean primitive. Federation between swarms can
  exchange swarm keys (or per-channel sub-keys) under explicit policy, replacing
  the current OGP-lite signed-message scheme with end-to-end authenticated
  channels.

### What this does *not* change

- A compromised agent that legitimately holds the swarm key can still write
  poisoned content. The 18-pattern adversarial scanner is still the layer that
  catches this. AEAD prevents *forgery from outside*, not *betrayal from inside* —
  and biology is the same: a worker bee that has gone rogue still smells right.
- Key compromise is catastrophic. Key rotation (`swarm key rotate`) and a
  short-lived per-session subkey scheme are part of the planned design.
- HMAC stays. The signing identity is a separate concern from payload
  confidentiality, and per-entry HMAC remains the simplest way to prove "this
  exact record was written by this exact agent" inside an already-decrypted
  trail.

### Phasing

- **Phase 1** — swarm key generation, AEAD-sealed `trail.log`, `swarm key rotate`.
- **Phase 2** — extend AEAD to `memory.md`, `state.md` decision entries, and
  claim notes; transparent decryption in `swarm` reads.
- **Phase 3** — federation: swarm-to-swarm key exchange under Doorman policy,
  replacing file-based OGP-lite with authenticated channels.

XChaCha20-Poly1305 was chosen for nonce-misuse resistance (24-byte random
nonces) and stdlib-adjacent availability (`pynacl` or `cryptography` — both
already common in the dependency closure of any project running an agent SDK).

---

## Threat model summary

| Threat | Mitigated by | Residual risk |
|--------|-------------|---------------|
| Compromised agent writes to `.swarm/` | Adversarial scanner + signed trail | Novel patterns evade scanner |
| Stale claim locks out work | Pheromone decay in `swarm audit` | None for honest timeouts |
| Trail tampered after the fact | HMAC-SHA256 per entry in trail.log | Key compromise |
| History exposed via git push | Trail invisible by default | User opts in knowingly |
| Cross-swarm identity spoofing | Fingerprint-indexed peer records | No PKI; HMAC only |
| LLM prompt injection via shared medium | 18-pattern scanner | Zero-day patterns |
| Rogue federation message | Doorman: policy → peer record → runtime | Transport-layer attacks |
