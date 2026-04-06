"""dot_swarm OGP-lite federation layer.

Implements cross-swarm trust and intent messaging following OGP semantics
without requiring a network gateway. The "transport" is filesystem exchange
(git push/pull, shared directory, or manual file copy).

Key design decisions informed by OGP build experience (David Proctor, Trilogy AI):
  - Identity = derived from signing key fingerprint, NOT from path/address.
    Paths change; cryptographic fingerprints do not.
  - Never trust the sender's claimed identity. Always look up from stored
    trusted_peers/ — doorman_check() enforces this on every inbound message.
  - Persist peer record BEFORE returning success (the addPeer() lesson).
  - Three-layer scope model:
      Layer 1: policy.md  — what intents this swarm accepts globally
      Layer 2: trusted_peers/<fp>.json — per-peer permissions
      Layer 3: doorman_check() — runtime enforcement on every inbound op

Signing limitation: HMAC-SHA256 is symmetric, so outbound signatures are
useful for trail integrity but cannot be independently verified by peers
without pre-sharing the key. Ed25519 (asymmetric) is the natural upgrade
path to full OGP compatibility. See docs/INTEGRATION_PLAN.md.

Directory layout (all inside .swarm/):
  federation/
    trusted_peers/<fingerprint>.json  — peer trust records
    inbox/<ts>_<intent>_<fp8>.json   — inbound intent messages
    outbox/<ts>_<intent>_<fp8>.json  — outbound intent messages
    policy.md                         — Layer 1 global intent policy
    exports.md                        — what context this swarm shares
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from dot_swarm.signing import (
    IDENTITY_FILE,
    SIGNING_KEY_FILE,
    _sign,
    load_identity,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEDERATION_DIR = "federation"
TRUSTED_PEERS_DIR = "federation/trusted_peers"
INBOX_DIR = "federation/inbox"
OUTBOX_DIR = "federation/outbox"
POLICY_FILE = "federation/policy.md"
EXPORTS_FILE = "federation/exports.md"

INTENT_WORK_REQUEST = "work_request"
INTENT_ALIGNMENT_SIGNAL = "alignment_signal"
INTENT_CAPABILITY_AD = "capability_ad"
INTENT_ACK = "ack"

ALL_INTENTS: frozenset[str] = frozenset(
    {INTENT_WORK_REQUEST, INTENT_ALIGNMENT_SIGNAL, INTENT_CAPABILITY_AD, INTENT_ACK}
)
DEFAULT_SCOPES: list[str] = [INTENT_WORK_REQUEST, INTENT_ALIGNMENT_SIGNAL]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FederationPeer:
    swarm_id: str
    fingerprint: str
    display_name: str
    trusted_at: str
    scopes: list[str]


@dataclass
class FederationMessage:
    version: str
    timestamp: str
    from_swarm: str
    from_fingerprint: str
    to_fingerprint: str
    intent: str
    payload: dict
    signature: str
    source_file: Path | None = None


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_federation(swarm_path: Path) -> None:
    """Create .swarm/federation/ directory structure. Idempotent."""
    for subdir in [FEDERATION_DIR, TRUSTED_PEERS_DIR, INBOX_DIR, OUTBOX_DIR]:
        (swarm_path / subdir).mkdir(parents=True, exist_ok=True)

    policy_file = swarm_path / POLICY_FILE
    if not policy_file.exists():
        _atomic_write(policy_file, _default_policy_md())

    exports_file = swarm_path / EXPORTS_FILE
    if not exports_file.exists():
        _atomic_write(exports_file, _default_exports_md())


# ---------------------------------------------------------------------------
# Peer trust management
# ---------------------------------------------------------------------------

def trust_peer(
    swarm_path: Path,
    peer_identity_path: Path,
    display_name: str = "",
    scopes: list[str] | None = None,
) -> FederationPeer:
    """Import a peer's identity.json and add them to trusted_peers/.

    OGP lesson: persist the peer record BEFORE returning success.
    We always derive peer identity from the stored fingerprint, never
    from whatever the peer claims in a message header.
    """
    raw = json.loads(peer_identity_path.read_text())
    fingerprint = raw.get("fingerprint", "")
    if not fingerprint:
        raise ValueError(
            f"peer identity file {peer_identity_path} has no 'fingerprint' field"
        )

    peer = FederationPeer(
        swarm_id=raw.get("id", fingerprint),
        fingerprint=fingerprint,
        display_name=display_name or raw.get("id", fingerprint),
        trusted_at=_utcnow(),
        scopes=scopes if scopes is not None else DEFAULT_SCOPES,
    )

    # Persist first — addPeer() lesson from OGP
    peer_file = swarm_path / TRUSTED_PEERS_DIR / f"{fingerprint}.json"
    _atomic_write(peer_file, json.dumps(asdict(peer), indent=2))
    return peer


def revoke_peer(swarm_path: Path, fingerprint: str) -> bool:
    """Remove a peer from trusted_peers/. Returns True if found."""
    peer_file = swarm_path / TRUSTED_PEERS_DIR / f"{fingerprint}.json"
    if peer_file.exists():
        peer_file.unlink()
        return True
    return False


def list_peers(swarm_path: Path) -> list[FederationPeer]:
    """Return all trusted peers, sorted by display name."""
    peers_dir = swarm_path / TRUSTED_PEERS_DIR
    if not peers_dir.exists():
        return []
    result: list[FederationPeer] = []
    for f in sorted(peers_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            result.append(FederationPeer(**data))
        except Exception:
            pass
    return sorted(result, key=lambda p: p.display_name)


def get_peer(swarm_path: Path, fingerprint: str) -> FederationPeer | None:
    """Look up a single trusted peer by fingerprint."""
    peer_file = swarm_path / TRUSTED_PEERS_DIR / f"{fingerprint}.json"
    if not peer_file.exists():
        return None
    try:
        return FederationPeer(**json.loads(peer_file.read_text()))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Layer 3: Doorman enforcement
# ---------------------------------------------------------------------------

def doorman_check(
    swarm_path: Path,
    fingerprint: str,
    intent: str,
) -> tuple[bool, str]:
    """Runtime enforcement of the three-layer scope model.

    Layer 2: Is this fingerprint in trusted_peers? Does their scope
             include this intent?
    Layer 1: Does policy.md permit this intent globally?

    OGP lesson: identity is always derived from stored peer records —
    we never trust the from_fingerprint field in the message itself.
    The caller is responsible for passing the fingerprint from the
    stored message body, not from a claimed header.

    Returns (allowed: bool, reason: str).
    """
    peer = get_peer(swarm_path, fingerprint)
    if peer is None:
        return False, f"unknown fingerprint {fingerprint!r} — not in trusted peers"
    if intent not in peer.scopes:
        return False, (
            f"peer {peer.display_name!r} does not have scope for intent {intent!r}; "
            f"allowed: {peer.scopes}"
        )
    if not _policy_allows(swarm_path, intent):
        return False, f"intent {intent!r} is disabled in federation/policy.md"
    return True, "ok"


# ---------------------------------------------------------------------------
# Message signing (outbound)
# ---------------------------------------------------------------------------

def sign_federation_message(key_bytes: bytes, msg: dict) -> str:
    """HMAC-SHA256 sign a federation message dict (excludes 'signature' key)."""
    canonical = _canonical_json(msg)
    return _hmac.new(key_bytes, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_federation_message(key_bytes: bytes, msg: dict, signature: str) -> bool:
    """Verify a federation message HMAC signature. Returns False on any error."""
    try:
        expected = sign_federation_message(key_bytes, msg)
        return _hmac.compare_digest(expected, signature)
    except Exception:
        return False


def _canonical_json(d: dict) -> str:
    """Deterministic JSON for signing — 'signature' key excluded."""
    return json.dumps(
        {k: v for k, v in d.items() if k != "signature"},
        sort_keys=True,
        separators=(",", ":"),
    )


# ---------------------------------------------------------------------------
# Outbox: creating outbound messages
# ---------------------------------------------------------------------------

def write_outbox(
    swarm_path: Path,
    to_fingerprint: str,
    intent: str,
    payload: dict,
    agent_id: str = "local",
) -> Path:
    """Create a signed intent message in outbox/.

    Caller delivers the file to the peer via git, shared directory,
    or any other transport. The message is HMAC-signed with this swarm's
    key for local trail integrity; note that the recipient cannot
    independently verify the HMAC without key exchange (see module docstring).
    """
    key_file = swarm_path / SIGNING_KEY_FILE
    if not key_file.exists():
        raise FileNotFoundError(
            f"No signing key at {key_file}. Run 'swarm init' first."
        )
    key_bytes = key_file.read_text().strip().encode()

    identity = load_identity(swarm_path)
    if identity is None:
        raise FileNotFoundError(
            f"No identity at {swarm_path / IDENTITY_FILE}. Run 'swarm init' first."
        )

    ts = _utcnow()
    msg: dict = {
        "version": "1",
        "timestamp": ts,
        "from_swarm": identity["id"],
        "from_fingerprint": identity["fingerprint"],
        "to_fingerprint": to_fingerprint,
        "intent": intent,
        "payload": payload,
        "agent_id": agent_id,
        "signature": "",
    }
    msg["signature"] = sign_federation_message(key_bytes, msg)

    safe_intent = re.sub(r"[^a-z0-9_]", "_", intent)
    filename = f"{ts.replace(':', '').replace('-', '')}_{safe_intent}_{to_fingerprint[:8]}.json"
    out_path = swarm_path / OUTBOX_DIR / filename

    init_federation(swarm_path)
    _atomic_write(out_path, json.dumps(msg, indent=2))
    return out_path


# ---------------------------------------------------------------------------
# Inbox: reading and applying inbound messages
# ---------------------------------------------------------------------------

def read_inbox(swarm_path: Path) -> list[FederationMessage]:
    """Return all messages in inbox/, parsed, oldest-first."""
    inbox_dir = swarm_path / INBOX_DIR
    if not inbox_dir.exists():
        return []
    messages: list[FederationMessage] = []
    for f in sorted(inbox_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            messages.append(FederationMessage(
                version=data.get("version", "1"),
                timestamp=data["timestamp"],
                from_swarm=data.get("from_swarm", ""),
                from_fingerprint=data["from_fingerprint"],
                to_fingerprint=data.get("to_fingerprint", ""),
                intent=data["intent"],
                payload=data.get("payload", {}),
                signature=data.get("signature", ""),
                source_file=f,
            ))
        except Exception:
            pass
    return messages


def deliver_to_inbox(swarm_path: Path, message_file: Path) -> Path:
    """Copy a peer's outbox message file into our inbox/."""
    inbox_dir = swarm_path / INBOX_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)
    dest = inbox_dir / message_file.name
    dest.write_bytes(message_file.read_bytes())
    return dest


def apply_inbox_message(
    swarm_path: Path,
    message_file: Path,
    add_item_fn: Callable,
    paths: object,
) -> dict:
    """Apply an inbox message to this swarm's queue/state.

    Sequence:
      1. Parse the message file.
      2. Doorman check (Layer 3) using the stored fingerprint from the
         message body — never trusting a claimed identity.
      3. Route to the appropriate queue operation.

    Returns {"ok": bool, "reason": str, "result": any}
    """
    try:
        data = json.loads(message_file.read_text())
    except Exception as exc:
        return {"ok": False, "reason": f"parse error: {exc}", "result": None}

    fingerprint = data.get("from_fingerprint", "")
    intent = data.get("intent", "")

    allowed, reason = doorman_check(swarm_path, fingerprint, intent)
    if not allowed:
        return {"ok": False, "reason": f"doorman blocked: {reason}", "result": None}

    payload = data.get("payload", {})

    if intent == INTENT_WORK_REQUEST:
        desc = payload.get("description", "(no description from peer)")
        ctx = payload.get("context", "")
        notes = f"Federation work_request from {fingerprint[:8]}" + (f" — {ctx}" if ctx else "")
        result = add_item_fn(paths, desc, notes=notes, priority="medium")
        return {"ok": True, "reason": "work_request added to queue", "result": str(result)}

    if intent in (INTENT_ALIGNMENT_SIGNAL, INTENT_CAPABILITY_AD, INTENT_ACK):
        return {"ok": True, "reason": f"{intent} acknowledged (informational)", "result": payload}

    return {"ok": False, "reason": f"unrecognised intent: {intent!r}", "result": None}


# ---------------------------------------------------------------------------
# Identity export
# ---------------------------------------------------------------------------

def export_identity(swarm_path: Path) -> dict:
    """Return the public identity dict — safe to share with federation peers."""
    identity = load_identity(swarm_path)
    if identity is None:
        raise FileNotFoundError(
            f"No signing identity at {swarm_path}. Run 'swarm init' first."
        )
    return identity


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _policy_allows(swarm_path: Path, intent: str) -> bool:
    """Layer 1: check policy.md for disabled intents. Default: allow all known."""
    policy_file = swarm_path / POLICY_FILE
    if not policy_file.exists():
        return intent in ALL_INTENTS
    content = policy_file.read_text()
    return f"disabled: {intent}" not in content


def _default_policy_md() -> str:
    return """\
# Federation Policy

Controls which intents this swarm accepts from federated peers.
To disable an intent, add a line: `disabled: <intent_type>`

## Permitted Intents

All intents are enabled by default:

- `work_request` — peer asks this swarm to take on a work item
- `alignment_signal` — peer shares alignment status (read-only)
- `capability_ad` — peer advertises its capabilities (informational)
- `ack` — peer acknowledges a message
"""


def _default_exports_md() -> str:
    return """\
# Federation Exports

Declares what information this swarm shares with federation peers.

## Exported

- [ ] Queue summary (pending item titles only — no notes or agent IDs)
- [ ] Context summary (division purpose + current focus)

## Not Exported

- Memory entries (internal decisions, sensitive context)
- Full queue notes and agent identifiers
- State.md blocker details
- Trail log
"""
