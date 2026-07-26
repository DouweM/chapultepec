"""Tests for the ActivityTimes temporal-set schedule evaluator."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pychapultepec.schedule import expand

TZ = ZoneInfo("America/Mexico_City")

# "Lanchas Puerto Chico": Tue-Sun 09:00-16:30 (Monday closed).
LANCHAS = {
    "type": "intersection",
    "children": [
        {
            "type": "period",
            "offset_date": "2018-01-02 00:00:00",
            "period_length": {"day": 7},
            "range_length": {"day": 6},
        },
        {
            "type": "period",
            "offset_date": "2020-01-01 09:00:00",
            "period_length": {"day": 1},
            "range_length": {"minute": 450},
        },
    ],
}

# "Arma tu dinosaurio": a specific Sunday at 12:00 (instant).
DINO = {
    "type": "intersection",
    "children": [
        {"type": "range", "start": "2026-07-26 00:00:00", "end": "2026-07-27 00:00:00"},
        {
            "type": "period",
            "offset_date": "2018-01-07 00:00:00",
            "period_length": {"day": 7},
            "range_length": {"day": 1},
        },
        {"type": "period", "offset_date": "2020-01-01 12:00:00", "period_length": {"day": 1}},
    ],
}


def _window(start: str, end: str) -> tuple[datetime, datetime]:
    return datetime.fromisoformat(start).replace(tzinfo=TZ), datetime.fromisoformat(end).replace(tzinfo=TZ)


def test_weekly_daily_intersection() -> None:
    """Lanchas yields Tue-Sun 09:00-16:30 and skips Monday."""
    lo, hi = _window("2026-07-26 00:00", "2026-08-02 00:00")  # Sun..Sun
    occ = expand(LANCHAS, lo, hi, TZ)
    days = {o.start.date().isoformat() for o in occ}
    assert "2026-07-27" not in days  # Monday closed
    assert "2026-07-28" in days  # Tuesday open
    for o in occ:
        assert (o.start.hour, o.start.minute) == (9, 0)
        assert (o.end.hour, o.end.minute) == (16, 30)


def test_instant_on_specific_day() -> None:
    """The dinosaur workshop is a single instant on the target Sunday at 12:00."""
    lo, hi = _window("2026-07-20 00:00", "2026-08-03 00:00")
    occ = expand(DINO, lo, hi, TZ)
    assert len(occ) == 1
    only = occ[0]
    assert only.is_instant
    assert only.start.isoformat() == "2026-07-26T12:00:00-06:00"


def test_empty_window_outside_range() -> None:
    """A fixed-range schedule yields nothing outside that range."""
    lo, hi = _window("2027-01-01 00:00", "2027-01-08 00:00")
    assert expand(DINO, lo, hi, TZ) == []


def test_range_node() -> None:
    """An absolute range is clipped to the query window."""
    schedule = {"type": "range", "start": "2026-07-26 05:00:00", "end": "2026-07-26 18:00:00"}
    lo, hi = _window("2026-07-26 00:00", "2026-07-27 00:00")
    occ = expand(schedule, lo, hi, TZ)
    assert len(occ) == 1
    assert (occ[0].start.hour, occ[0].end.hour) == (5, 18)
