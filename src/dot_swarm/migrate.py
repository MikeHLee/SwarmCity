"""dot_swarm legacy-layout migration.

The v1.0 protocol expects every ``.swarm/`` directory to contain:

  * ``claims/``                            — append-only claim trail (SWC-033)
  * ``federation/strangers/``              — untrusted message bay
  * ``federation/strangers/rejected/``     — rejected-message archive
  * ``.gitignore``                         — must list ``.swarm_key`` and
                                             ``.swarm_key.old`` alongside the
                                             existing ``.signing_key`` entry

Older directories created by 0.3.x or earlier may be missing some of these.
``swarm migrate`` is a small, idempotent fix-up pass that brings any
``.swarm/`` directory up to the v1.0 layout without touching content. It
also backfills a synthetic claim record for each item that is currently
``CLAIMED`` in ``queue.md`` but has no record in ``claims/``, so the
resolver renders the same state before and after the migration.

The migration is intentionally append-only and safe to re-run: every step
checks for the desired end state first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .models import Claim, ItemState, SwarmPaths, utcnow
from .operations import read_queue, write_claim


REQUIRED_GITIGNORE_ENTRIES = (
    ".signing_key",
    ".swarm_key",
    ".swarm_key.old",
    "quarantine/",
    "trail.log",
)


@dataclass
class MigrationReport:
    swarm_path: Path
    actions: list[str] = field(default_factory=list)
    needed: list[str] = field(default_factory=list)
    backfilled_claims: int = 0
    already_current: bool = True

    def record(self, msg: str, applied: bool) -> None:
        (self.actions if applied else self.needed).append(msg)
        self.already_current = False


def migrate_swarm(swarm_path: Path, dry_run: bool = False) -> MigrationReport:
    """Bring one ``.swarm/`` directory up to the v1.0 layout.

    With ``dry_run=True``, every check still runs but no files are written;
    the report's ``needed`` field lists what *would* change. With
    ``dry_run=False``, missing layout pieces are created and the
    ``actions`` field lists what was applied.
    """
    report = MigrationReport(swarm_path=swarm_path)

    # 1. claims/ directory
    claims_dir = swarm_path / "claims"
    if not claims_dir.is_dir():
        if not dry_run:
            claims_dir.mkdir(parents=True, exist_ok=True)
        report.record("create claims/ (append-only claim trail)", applied=not dry_run)

    # 2. federation/strangers and federation/strangers/rejected
    federation_dir = swarm_path / "federation"
    if federation_dir.is_dir():
        for sub in ("strangers", "strangers/rejected"):
            target = federation_dir / sub
            if not target.is_dir():
                if not dry_run:
                    target.mkdir(parents=True, exist_ok=True)
                report.record(
                    f"create federation/{sub}/ (untrusted message bay)",
                    applied=not dry_run,
                )

    # 3. .gitignore entries
    gitignore = swarm_path / ".gitignore"
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8")
        missing = [e for e in REQUIRED_GITIGNORE_ENTRIES if e not in existing]
        if missing:
            if not dry_run:
                with gitignore.open("a", encoding="utf-8") as fh:
                    fh.write("\n" + "\n".join(missing) + "\n")
            report.record(
                f"add gitignore entries: {', '.join(missing)}",
                applied=not dry_run,
            )
    else:
        if not dry_run:
            gitignore.write_text("\n".join(REQUIRED_GITIGNORE_ENTRIES) + "\n", encoding="utf-8")
        report.record(
            ".swarm/.gitignore was missing — created with required entries",
            applied=not dry_run,
        )

    # 4. Backfill synthetic claim records for items CLAIMED in queue.md
    #    but absent from claims/. Without this, the resolver would re-open
    #    them as OPEN on the next read after we mkdir claims/.
    paths = SwarmPaths.from_swarm_dir(swarm_path)
    if paths.queue.exists():
        # Read queue without resolving claims (raw queue.md state)
        from .operations import _parse_items, _split_sections
        text = paths.queue.read_text(encoding="utf-8")
        sections = _split_sections(text)
        active_raw = _parse_items(sections.get("Active", ""))

        existing_claim_files = (
            {p.name for p in claims_dir.glob("*.json")} if claims_dir.is_dir() else set()
        )

        active_states = {
            ItemState.CLAIMED, ItemState.PARTIAL, ItemState.COMPETING, ItemState.REVIEW,
        }
        for item in active_raw:
            if item.state not in active_states:
                continue
            if item.claimed_by is None or item.claimed_at is None:
                continue
            # Already has a record?
            if any(name.startswith(f"{item.id}_") for name in existing_claim_files):
                continue
            if dry_run:
                report.record(
                    f"backfill claim record for {item.id} ({item.state.value} by {item.claimed_by})",
                    applied=False,
                )
            else:
                # ensure claims/ exists for the backfill
                claims_dir.mkdir(parents=True, exist_ok=True)
                write_claim(paths, Claim(
                    item_id=item.id,
                    agent_id=item.claimed_by,
                    state=item.state,
                    timestamp=item.claimed_at or utcnow(),
                    note=f"backfilled-by-swarm-migrate from queue.md",
                ))
                report.backfilled_claims += 1
                report.record(
                    f"backfill claim record for {item.id} ({item.state.value} by {item.claimed_by})",
                    applied=True,
                )

    return report


def migrate_tree(root: Path, dry_run: bool = False, depth: int = 3) -> list[MigrationReport]:
    """Run migrate_swarm against every .swarm/ found under root."""
    from .operations import discover_divisions
    reports: list[MigrationReport] = []
    for _div_path, paths in discover_divisions(root, depth=depth):
        reports.append(migrate_swarm(paths.root, dry_run=dry_run))
    return reports
