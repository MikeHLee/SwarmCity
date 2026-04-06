"""dot_swarm scheduler.

Cron-style and event-driven scheduling, stored in .swarm/schedules.md.
No daemon — designed to be called from the user's system crontab or
manually via `swarm schedule run-due`. Stdlib only; no croniter dep.

Schedule types:
  cron      — standard 5-field cron expression (minute hour dom month dow)
  interval  — every N minutes/hours/days
  on:done   — fires when a specific item_id transitions to DONE
  on:blocked — fires when a specific item_id is BLOCKED
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

SCHEDULES_FILE = "schedules.md"

_ID_RE = re.compile(r"^- \[[\w:]+\] \[(SCHED-\d+)\] `([^`]+)` → (.+)$")
_FIELD_RE = re.compile(r"^\s+(notes|last_run|enabled): (.+)$")
_NEXT_ID_RE = re.compile(r"SCHED-(\d+)")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Schedule:
    id: str              # e.g. "SCHED-001"
    name: str            # human-readable label (may equal spec summary)
    stype: str           # "cron" | "interval" | "on:done" | "on:blocked"
    spec: str            # cron expr, interval string, or item_id
    command: str         # full shell command or swarm sub-command
    last_run: str = ""   # ISO timestamp of last execution, or ""
    enabled: bool = True
    notes: str = ""

    def to_md(self) -> str:
        marker = "cron" if self.stype == "cron" else self.stype
        lines = [f"- [{marker}] [{self.id}] `{self.spec}` → {self.command}"]
        if self.name and self.name != self.id:
            lines[0] = f"- [{marker}] [{self.id}] `{self.spec}` → {self.command}  # {self.name}"
        inner = []
        if self.notes:
            inner.append(f"      notes: {self.notes}")
        if self.last_run:
            inner.append(f"      last_run: {self.last_run}")
        if not self.enabled:
            inner.append("      enabled: false")
        return "\n".join([lines[0]] + inner)


@dataclass
class RunResult:
    schedule_id: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    ran_at: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_schedules(swarm_path: Path) -> list[Schedule]:
    """Parse .swarm/schedules.md into Schedule objects."""
    sfile = swarm_path / SCHEDULES_FILE
    if not sfile.exists():
        return []

    schedules: list[Schedule] = []
    current: Schedule | None = None

    for raw in sfile.read_text(encoding="utf-8").splitlines():
        m = _ID_RE.match(raw)
        if m:
            sid, spec, command = m.group(1), m.group(2), m.group(3).split("  #")[0].strip()
            name_comment = raw.split("  #", 1)[1].strip() if "  #" in raw else sid
            stype = _infer_stype(spec)
            current = Schedule(id=sid, name=name_comment, stype=stype,
                               spec=spec, command=command)
            schedules.append(current)
            continue

        if current is not None:
            fm = _FIELD_RE.match(raw)
            if fm:
                key, val = fm.group(1), fm.group(2).strip()
                if key == "notes":
                    current.notes = val
                elif key == "last_run":
                    current.last_run = val
                elif key == "enabled":
                    current.enabled = val.lower() not in ("false", "0", "no")

    return schedules


def save_schedules(swarm_path: Path, schedules: list[Schedule]) -> None:
    """Write schedules back to .swarm/schedules.md."""
    sfile = swarm_path / SCHEDULES_FILE
    lines = ["# Schedules", "", "## Active", ""]
    active = [s for s in schedules if s.enabled]
    for s in active:
        lines.append(s.to_md())
        lines.append("")
    if not active:
        lines.append("(none)")
        lines.append("")
    disabled = [s for s in schedules if not s.enabled]
    if disabled:
        lines += ["## Disabled", ""]
        for s in disabled:
            lines.append(s.to_md())
            lines.append("")
    sfile.write_text("\n".join(lines), encoding="utf-8")


def add_schedule(
    swarm_path: Path,
    name: str,
    stype: str,
    spec: str,
    command: str,
    notes: str = "",
) -> Schedule:
    """Add a new schedule and persist it."""
    schedules = load_schedules(swarm_path)
    next_num = _next_schedule_num(schedules)
    sid = f"SCHED-{next_num:03d}"
    sched = Schedule(id=sid, name=name, stype=stype, spec=spec,
                     command=command, notes=notes)
    schedules.append(sched)
    save_schedules(swarm_path, schedules)
    return sched


def remove_schedule(swarm_path: Path, schedule_id: str) -> bool:
    """Remove a schedule by ID. Returns True if removed."""
    schedules = load_schedules(swarm_path)
    before = len(schedules)
    schedules = [s for s in schedules if s.id != schedule_id]
    if len(schedules) == before:
        return False
    save_schedules(swarm_path, schedules)
    return True


def _next_schedule_num(schedules: list[Schedule]) -> int:
    nums = [int(m.group(1)) for s in schedules
            if (m := _NEXT_ID_RE.match(s.id))]
    return max(nums, default=0) + 1


# ---------------------------------------------------------------------------
# Due-checking
# ---------------------------------------------------------------------------

def is_due(schedule: Schedule, now: datetime | None = None) -> bool:
    """Return True if schedule should fire now given last_run."""
    if not schedule.enabled:
        return False
    now = now or datetime.now(timezone.utc)
    last = _parse_ts(schedule.last_run) if schedule.last_run else None

    if schedule.stype == "cron":
        return _cron_is_due(schedule.spec, last, now)
    elif schedule.stype == "interval":
        if last is None:
            return True
        delta = _parse_interval(schedule.spec)
        return delta is not None and (now - last) >= delta
    elif schedule.stype in ("on:done", "on:blocked"):
        return False  # event-driven — checked externally via get_event_triggers()
    return False


def get_event_triggers(
    swarm_path: Path, event: str, item_id: str
) -> list[Schedule]:
    """Return schedules triggered by a specific event (on:done / on:blocked) for item_id."""
    return [
        s for s in load_schedules(swarm_path)
        if s.enabled and s.stype == event and s.spec == item_id
    ]


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_schedule(swarm_path: Path, schedule: Schedule) -> RunResult:
    """Execute a schedule's command and update last_run."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    try:
        result = subprocess.run(
            schedule.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(swarm_path.parent),
        )
        exit_code = result.returncode
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
    except subprocess.TimeoutExpired:
        exit_code = 124
        stdout = ""
        stderr = "timeout after 300s"
    except Exception as exc:
        exit_code = 1
        stdout = ""
        stderr = str(exc)

    run_result = RunResult(
        schedule_id=schedule.id,
        command=schedule.command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        ran_at=now_str,
    )

    schedules = load_schedules(swarm_path)
    for s in schedules:
        if s.id == schedule.id:
            s.last_run = now_str
            break
    save_schedules(swarm_path, schedules)
    return run_result


def run_due(swarm_path: Path) -> list[RunResult]:
    """Run all currently-due cron/interval schedules. Returns results."""
    now = datetime.now(timezone.utc)
    results: list[RunResult] = []
    for schedule in load_schedules(swarm_path):
        if is_due(schedule, now):
            results.append(run_schedule(swarm_path, schedule))
    return results


# ---------------------------------------------------------------------------
# Minimal cron evaluator (stdlib, no croniter)
# ---------------------------------------------------------------------------

def _cron_is_due(expr: str, last: datetime | None, now: datetime) -> bool:
    """True if the cron expression fired at least once between last and now.

    Scans forward from (last + 1 min) up to now in 1-minute increments,
    capped at 10 080 minutes (7 days) for safety.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return False  # not a valid 5-field cron
    try:
        fields = [_parse_cron_field(p, lo, hi) for p, (lo, hi) in zip(
            parts, [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
        )]
    except ValueError:
        return False

    start = (last + timedelta(minutes=1)) if last else (now - timedelta(minutes=1))
    # Align start to minute boundary
    start = start.replace(second=0, microsecond=0)
    limit = 10_080  # max minutes to scan
    t = start
    for _ in range(limit):
        if t > now:
            break
        if (t.minute in fields[0]
                and t.hour in fields[1]
                and t.day in fields[2]
                and t.month in fields[3]
                and t.weekday() in _dow_set(fields[4])):
            return True
        t += timedelta(minutes=1)
    return False


def _parse_cron_field(expr: str, lo: int, hi: int) -> frozenset[int]:
    """Return frozenset of matching values for a single cron field."""
    if expr == "*":
        return frozenset(range(lo, hi + 1))

    result: set[int] = set()
    for part in expr.split(","):
        if "/" in part:
            base, step_s = part.split("/", 1)
            step = int(step_s)
            if base == "*":
                values = range(lo, hi + 1)
            elif "-" in base:
                a, b = base.split("-", 1)
                values = range(int(a), int(b) + 1)
            else:
                values = range(int(base), hi + 1)
            result.update(v for v in values if (v - lo) % step == 0 or base != "*")
            result.update(range(lo, hi + 1, step) if base == "*" else
                          [v for v in values if v % step == 0])
        elif "-" in part:
            a, b = part.split("-", 1)
            result.update(range(int(a), int(b) + 1))
        else:
            result.add(int(part))
    return frozenset(v for v in result if lo <= v <= hi)


def _dow_set(field: frozenset[int]) -> frozenset[int]:
    """Convert cron dow (0=Sunday, 6=Saturday) to Python weekday (0=Mon, 6=Sun)."""
    mapping = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    return frozenset(mapping[d] for d in field if d in mapping)


def _parse_interval(spec: str) -> timedelta | None:
    """Parse '30m', '6h', '2d' → timedelta."""
    m = re.fullmatch(r"(\d+)\s*([mhd])", spec.strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return {"m": timedelta(minutes=n), "h": timedelta(hours=n), "d": timedelta(days=n)}[unit]


def _infer_stype(spec: str) -> str:
    s = spec.strip()
    if s.startswith("on:"):
        return s.split()[0]  # "on:done" or "on:blocked"
    if re.fullmatch(r"\d+\s*[mhd]", s):
        return "interval"
    return "cron"


def _parse_ts(s: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
