"""Tests for dot_swarm.scheduler — cron/interval/event scheduling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from dot_swarm.scheduler import (
    SCHEDULES_FILE,
    RunResult,
    Schedule,
    add_schedule,
    get_event_triggers,
    is_due,
    load_schedules,
    remove_schedule,
    save_schedules,
    _cron_is_due,
    _infer_stype,
    _parse_interval,
    _parse_ts,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def swarm_dir(tmp_path: Path) -> Path:
    swarm = tmp_path / ".swarm"
    swarm.mkdir()
    return swarm


def _ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------

def test_empty_schedules_file_returns_empty(swarm_dir: Path) -> None:
    assert load_schedules(swarm_dir) == []


def test_add_schedule_persists(swarm_dir: Path) -> None:
    s = add_schedule(swarm_dir, "Heal", "cron", "0 */6 * * *", "swarm heal --fix")
    assert s.id == "SCHED-001"
    assert s.stype == "cron"
    loaded = load_schedules(swarm_dir)
    assert len(loaded) == 1
    assert loaded[0].id == "SCHED-001"
    assert loaded[0].command == "swarm heal --fix"


def test_add_multiple_schedules_incrementing_ids(swarm_dir: Path) -> None:
    add_schedule(swarm_dir, "A", "cron", "0 * * * *", "cmd-a")
    add_schedule(swarm_dir, "B", "interval", "6h", "cmd-b")
    add_schedule(swarm_dir, "C", "on:done", "on:done CLD-042", "cmd-c")
    ids = [s.id for s in load_schedules(swarm_dir)]
    assert ids == ["SCHED-001", "SCHED-002", "SCHED-003"]


def test_remove_schedule(swarm_dir: Path) -> None:
    add_schedule(swarm_dir, "X", "cron", "0 0 * * *", "echo x")
    assert remove_schedule(swarm_dir, "SCHED-001") is True
    assert load_schedules(swarm_dir) == []


def test_remove_nonexistent_returns_false(swarm_dir: Path) -> None:
    assert remove_schedule(swarm_dir, "SCHED-999") is False


def test_roundtrip_with_notes_and_last_run(swarm_dir: Path) -> None:
    s = Schedule(
        id="SCHED-001", name="Test", stype="cron",
        spec="0 9 * * 1", command="swarm audit",
        last_run="2026-04-06T09:00Z", notes="weekly",
    )
    save_schedules(swarm_dir, [s])
    loaded = load_schedules(swarm_dir)
    assert loaded[0].last_run == "2026-04-06T09:00Z"
    assert loaded[0].notes == "weekly"


def test_disabled_schedule_roundtrip(swarm_dir: Path) -> None:
    s = Schedule(id="SCHED-001", name="Off", stype="cron",
                 spec="* * * * *", command="echo x", enabled=False)
    save_schedules(swarm_dir, [s])
    loaded = load_schedules(swarm_dir)
    assert loaded[0].enabled is False


# ---------------------------------------------------------------------------
# _infer_stype
# ---------------------------------------------------------------------------

def test_infer_stype_cron() -> None:
    assert _infer_stype("0 */6 * * *") == "cron"


def test_infer_stype_interval() -> None:
    assert _infer_stype("6h") == "interval"
    assert _infer_stype("30m") == "interval"
    assert _infer_stype("2d") == "interval"


def test_infer_stype_on_done() -> None:
    assert _infer_stype("on:done CLD-042") == "on:done"


def test_infer_stype_on_blocked() -> None:
    assert _infer_stype("on:blocked CLD-001") == "on:blocked"


# ---------------------------------------------------------------------------
# _parse_interval
# ---------------------------------------------------------------------------

def test_parse_interval_minutes() -> None:
    d = _parse_interval("30m")
    assert d == timedelta(minutes=30)


def test_parse_interval_hours() -> None:
    assert _parse_interval("6h") == timedelta(hours=6)


def test_parse_interval_days() -> None:
    assert _parse_interval("2d") == timedelta(days=2)


def test_parse_interval_invalid() -> None:
    assert _parse_interval("weekly") is None
    assert _parse_interval("") is None


# ---------------------------------------------------------------------------
# _cron_is_due
# ---------------------------------------------------------------------------

def test_cron_every_minute_is_due_when_no_last_run() -> None:
    now = _ts("2026-04-06T12:00Z")
    assert _cron_is_due("* * * * *", None, now) is True


def test_cron_hourly_is_due_after_1_hour() -> None:
    last = _ts("2026-04-06T11:00Z")
    now = _ts("2026-04-06T12:00Z")
    assert _cron_is_due("0 * * * *", last, now) is True


def test_cron_hourly_not_due_after_30_min() -> None:
    last = _ts("2026-04-06T11:00Z")
    now = _ts("2026-04-06T11:30Z")
    assert _cron_is_due("0 * * * *", last, now) is False


def test_cron_every_6h_is_due() -> None:
    last = _ts("2026-04-06T06:00Z")
    now = _ts("2026-04-06T12:00Z")
    assert _cron_is_due("0 */6 * * *", last, now) is True


def test_cron_every_6h_not_due_at_1h() -> None:
    last = _ts("2026-04-06T06:00Z")
    now = _ts("2026-04-06T07:00Z")
    assert _cron_is_due("0 */6 * * *", last, now) is False


def test_cron_daily_at_9am_is_due() -> None:
    last = _ts("2026-04-05T09:00Z")
    now = _ts("2026-04-06T09:05Z")
    assert _cron_is_due("0 9 * * *", last, now) is True


def test_cron_daily_at_9am_not_due_before() -> None:
    last = _ts("2026-04-06T09:00Z")
    now = _ts("2026-04-06T09:00Z")
    assert _cron_is_due("0 9 * * *", last, now) is False  # exactly same time, no fire


def test_cron_invalid_expr_returns_false() -> None:
    assert _cron_is_due("bad expression", None, datetime.now(timezone.utc)) is False


def test_cron_specific_minute_and_hour() -> None:
    last = _ts("2026-04-06T14:29Z")
    now = _ts("2026-04-06T14:30Z")
    assert _cron_is_due("30 14 * * *", last, now) is True


def test_cron_step_expression() -> None:
    last = _ts("2026-04-06T11:00Z")
    now = _ts("2026-04-06T11:15Z")
    assert _cron_is_due("*/15 * * * *", last, now) is True


# ---------------------------------------------------------------------------
# is_due — integrated
# ---------------------------------------------------------------------------

def test_is_due_cron_no_last_run(swarm_dir: Path) -> None:
    s = Schedule(id="SCHED-001", name="t", stype="cron",
                 spec="* * * * *", command="echo hi", last_run="")
    now = datetime.now(timezone.utc)
    assert is_due(s, now) is True


def test_is_due_interval_first_run(swarm_dir: Path) -> None:
    s = Schedule(id="SCHED-001", name="t", stype="interval",
                 spec="1h", command="echo hi", last_run="")
    assert is_due(s, datetime.now(timezone.utc)) is True


def test_is_due_interval_not_elapsed(swarm_dir: Path) -> None:
    last = datetime.now(timezone.utc) - timedelta(minutes=30)
    s = Schedule(id="SCHED-001", name="t", stype="interval",
                 spec="1h", command="echo hi",
                 last_run=last.strftime("%Y-%m-%dT%H:%MZ"))
    assert is_due(s) is False


def test_is_due_interval_elapsed(swarm_dir: Path) -> None:
    last = datetime.now(timezone.utc) - timedelta(hours=2)
    s = Schedule(id="SCHED-001", name="t", stype="interval",
                 spec="1h", command="echo hi",
                 last_run=last.strftime("%Y-%m-%dT%H:%MZ"))
    assert is_due(s) is True


def test_is_due_on_done_always_false() -> None:
    s = Schedule(id="SCHED-001", name="t", stype="on:done",
                 spec="on:done CLD-042", command="echo done", last_run="")
    assert is_due(s) is False


def test_is_due_disabled_never_fires() -> None:
    s = Schedule(id="SCHED-001", name="t", stype="cron",
                 spec="* * * * *", command="echo hi", enabled=False)
    assert is_due(s) is False


# ---------------------------------------------------------------------------
# Event triggers
# ---------------------------------------------------------------------------

def test_get_event_triggers_empty(swarm_dir: Path) -> None:
    assert get_event_triggers(swarm_dir, "on:done", "CLD-042") == []


def test_get_event_triggers_matches(swarm_dir: Path) -> None:
    add_schedule(swarm_dir, "Chain", "on:done", "on:done CLD-042", "swarm ai 'claim CLD-043'")
    results = get_event_triggers(swarm_dir, "on:done", "on:done CLD-042")
    assert len(results) == 1
    assert results[0].command == "swarm ai 'claim CLD-043'"


def test_get_event_triggers_no_cross_match(swarm_dir: Path) -> None:
    add_schedule(swarm_dir, "A", "on:done", "on:done CLD-042", "cmd-a")
    assert get_event_triggers(swarm_dir, "on:done", "on:done CLD-099") == []


def test_get_event_triggers_disabled_excluded(swarm_dir: Path) -> None:
    s = Schedule(id="SCHED-001", name="Off", stype="on:done",
                 spec="on:done CLD-042", command="cmd", enabled=False)
    save_schedules(swarm_dir, [s])
    assert get_event_triggers(swarm_dir, "on:done", "on:done CLD-042") == []
