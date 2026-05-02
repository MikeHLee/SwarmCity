# Changelog

All notable changes to dot_swarm are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-05-02

The first stable release. The protocol is frozen for the v1.x line:
existing `.swarm/` directories created by 1.0 will be readable by every
1.x release, and `swarm migrate` brings any 0.3.x directory up to the
v1.0 layout idempotently.

### Added — append-only claim trail (SWC-033)
- `.swarm/claims/` is now a true immutable log. Every `claim`, `partial`,
  `done`, `block`, `reopen`, and `compete` operation appends one
  JSON record; release transitions write a superseding record rather
  than deleting prior ones.
- New resolver in `operations.resolve_claims`: newest-per-(item, agent),
  with terminal records winning over equally-recent active ones, and
  multiple concurrent active agents aggregating into `COMPETING`.
- New CLI: `swarm trail claims [--item ID]` to view full history.

### Added — competing claimants (SWC-039)
- `claim --compete` now records each rival as an independent claim
  record rather than overwriting the prior claimant.
- New helpers `competitors_for(paths, item_id)` and
  `promote_competitor(paths, item_id, winner, reason)` — the latter
  writes a fresh `CLAIMED` record for the winner and an
  `OPEN`/`lost-competition` record for each loser.
- New CLI: `swarm compete list <id>` and
  `swarm compete winner <id> <agent> --reason ...`.

### Added — hidden-in-plain-sight stigmergic seals
- New module `dot_swarm.seals`. A *seal* is an HMAC tag embedded inline
  as `<!-- 🐝 sw-seal v2 <agent>:<hex16> -->` — looks like ordinary
  markdown to outsiders, authenticates the writer to anyone with the
  swarm signing key, and detects content tampering on read.
- Status enum: `VALID` / `INVALID` / `MISSING` / `UNKEYED`. Foreign-swarm
  seals read as `INVALID` — the digital analogue of a wrong cuticular
  signature.
- v2 (16-hex / 64-bit tag) is the default; v1 (8-hex / 32-bit) seals
  remain accepted for backward compatibility.
- New CLI: `swarm seal sign <file>`, `swarm seal verify`,
  `swarm seal check <file>`.

### Added — collaborative-but-untrusted message bay
- `federation/strangers/` holds inbound messages from peers without a
  matching `trusted_peers/` record (or whose intent is disabled by
  policy). Each quarantined message is paired with a
  `<file>.json.reason.txt` recording the doorman verdict.
- `apply_inbox_message` now quarantines on doorman block by default;
  `triage_inbox` sweeps the inbox in bulk.
- `promote_stranger` trusts the peer with explicit scopes and replays
  the message into `inbox/`. `reject_stranger` archives without trust
  into `strangers/rejected/`.
- New CLI: `swarm federation triage`,
  `swarm federation strangers list/show/promote/reject`.

### Added — swarm key (SWC-046, Phase 1)
- New module `dot_swarm.vault`. `swarm key init` generates a per-swarm
  ChaCha20-Poly1305 key (`.swarm/.swarm_key`, 256-bit, gitignored).
- When the key is present, every `trail.log` entry is written as a
  one-line `swae1:<base64>` envelope (nonce + ciphertext + 128-bit AEAD
  tag) — opaque on disk, transparently decrypted by `read_trail` and
  the CLI.
- `swarm key rotate` generates a new key, retains the prior one as
  `.swarm_key.old`, and re-seals every existing envelope under the new
  key. Mid-rotation reads fall back to the old key.
- `swarm key seal <file>` / `swarm key open <file>` apply the same
  envelope format to any individual coordination file.
- New optional extra: `pip install 'dot-swarm[crypto]'` (pulls
  `cryptography>=42`).
- The CHaCha20-Poly1305 layer composes with the existing HMAC-signed
  trail and the new seals — the medium is shared, but the *language*
  of the medium is not.

### Added — `swarm migrate`
- Brings any 0.3.x `.swarm/` directory up to the v1.0 layout
  idempotently. Creates missing `claims/`, `federation/strangers/`,
  `federation/strangers/rejected/`, ensures `.gitignore` lists the new
  key files, and backfills synthetic claim records for items still
  marked CLAIMED in `queue.md`.
- `--dry-run` previews changes without writing; `--all` runs against
  every `.swarm/` discovered under the current path.

### Changed
- `swarm init` now creates `.swarm/claims/` and includes
  `.swarm_key` / `.swarm_key.old` in the auto-generated `.gitignore`.
- `apply_inbox_message` returns an additional `quarantined` boolean and
  no longer drops untrusted messages silently.
- Default seal format is now v2 (16-hex tag). Existing v1 seals continue
  to verify.

### Tests
- 240+ tests across the suite; full pass on Python 3.11 and 3.12.

## [0.3.x] and earlier

See git history. 0.3.x was the pre-stable iteration line; protocol
shape changed across point releases. Use `swarm migrate` to upgrade.
