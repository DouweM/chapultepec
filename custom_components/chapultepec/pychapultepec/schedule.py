"""Evaluator for Attractions.io temporal-set schedules.

Both ``Item.ActivityTimes`` (event schedules) and ``*.OpeningTimes`` (opening
hours) are encoded as a small set algebra over time. A schedule is a tree of
nodes; evaluating it against a query window yields a list of concrete
``(start, end)`` occurrences.

Node types
----------
``range``
    An absolute interval ``[start, end)``.
``period``
    A repeating window: anchored at ``offset_date`` and repeating every
    ``period_length``; within each repetition the "on" window is ``range_length``
    long. When ``range_length`` is omitted the period contributes instants
    (zero-length occurrences) at each anchor — e.g. "every day at 12:00".
``intersection`` / ``union`` / ``difference``
    Boolean combinations of child nodes.

Example:
-------
``Lanchas Puerto Chico`` decodes to::

    intersection(
        period(offset=2018-01-02 Tue, every 7d, for 6d),   # Tue-Sun (Mon off)
        period(offset=2020-01-01 09:00, every 1d, for 450m) # daily 09:00-16:30
    )

which over any week yields ``Tue..Sun 09:00-16:30``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from typing import Any

from dateutil.relativedelta import relativedelta

_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# A half-open interval [start, end]; end == start denotes an instant.
Interval = tuple[datetime, datetime]


@dataclass(frozen=True)
class Occurrence:
    """A single concrete occurrence of a schedule."""

    start: datetime
    end: datetime

    @property
    def is_instant(self) -> bool:
        """Whether the occurrence has no duration (a point in time)."""
        return self.end == self.start


def _parse_naive(value: str) -> datetime:
    """Parse a ``YYYY-MM-DD HH:MM:SS`` timestamp into a naive datetime."""
    return datetime.strptime(value, _DATE_FORMAT)  # noqa: DTZ007 - localized later


def _delta(spec: dict[str, int] | None) -> relativedelta | None:
    """Convert a ``{unit: n}`` length spec into a relativedelta.

    Supports second/minute/hour/day/week/month/year. Returns ``None`` for an
    absent/empty spec (an instantaneous period window).
    """
    if not spec:
        return None
    mapping = {
        "second": "seconds",
        "minute": "minutes",
        "hour": "hours",
        "day": "days",
        "week": "weeks",
        "month": "months",
        "year": "years",
    }
    kwargs: dict[str, int] = {}
    for unit, amount in spec.items():
        key = mapping.get(unit)
        if key is None:
            raise ValueError(f"Unknown schedule unit: {unit}")
        kwargs[key] = kwargs.get(key, 0) + amount
    return relativedelta(**kwargs)  # type: ignore[arg-type]


def _clip(intervals: list[Interval], lo: datetime, hi: datetime) -> list[Interval]:
    """Clip intervals to the window ``[lo, hi)``, preserving instants at the edge."""
    out: list[Interval] = []
    for start, end in intervals:
        s = max(start, lo)
        e = min(end, hi)
        if s < e or (s == e and start == end and lo <= start < hi):
            out.append((s, e))
    return out


def _intersect_two(a: list[Interval], b: list[Interval]) -> list[Interval]:
    """Intersect two interval lists, keeping instants that fall inside the other."""
    out: list[Interval] = []
    for a0, a1 in a:
        for b0, b1 in b:
            lo = max(a0, b0)
            hi = min(a1, b1)
            if lo < hi:
                out.append((lo, hi))
            elif lo == hi:
                # An instant survives if it lies within the other operand.
                a_instant = a0 == a1
                b_instant = b0 == b1
                if (a_instant and b0 <= lo < b1) or (b_instant and a0 <= lo < a1) or (a_instant and b_instant):
                    out.append((lo, hi))
    return out


def _union(intervals: list[Interval]) -> list[Interval]:
    """Merge overlapping/adjacent intervals into a normalised list."""
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged: list[Interval] = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _subtract(a: list[Interval], b: list[Interval]) -> list[Interval]:
    """Subtract interval list ``b`` from ``a``."""
    result = a
    for cut_start, cut_end in _union(b):
        next_result: list[Interval] = []
        for start, end in result:
            if cut_end <= start or cut_start >= end:
                next_result.append((start, end))
                continue
            if start < cut_start:
                next_result.append((start, cut_start))
            if cut_end < end:
                next_result.append((cut_end, end))
        result = next_result
    return result


def _period_intervals(node: dict[str, Any], lo: datetime, hi: datetime, tz: tzinfo) -> list[Interval]:
    """Enumerate a period node's windows overlapping ``[lo, hi)``."""
    offset = _parse_naive(node["offset_date"]).replace(tzinfo=tz)
    period = _delta(node.get("period_length"))
    if period is None:
        raise ValueError("period node requires period_length")
    window = _delta(node.get("range_length"))

    # Advance the anchor to just before the query window without stepping one at
    # a time across years of history: use the mean period length as an estimate,
    # then correct with a bounded walk.
    approx = _approx_seconds(period)
    if approx > 0 and offset < lo:
        steps = int((lo - offset).total_seconds() // approx) - 1
        if steps > 0:
            offset = offset + period * steps

    intervals: list[Interval] = []
    anchor = offset
    # Walk backwards a little in case the estimate overshot.
    while anchor > lo:
        anchor = anchor - period
    guard = 0
    while anchor < hi:
        end = anchor + window if window is not None else anchor
        if end >= lo:
            intervals.append((anchor, end))
        anchor = anchor + period
        guard += 1
        if guard > 100_000:  # pragma: no cover - runaway safety net
            raise ValueError("period expansion did not terminate")
    return intervals


def _approx_seconds(delta: relativedelta) -> float:
    """Rough length of a relativedelta in seconds, for step estimation."""
    return (
        delta.years * 365.25 * 86400
        + delta.months * 30.44 * 86400
        + delta.days * 86400
        + delta.hours * 3600
        + delta.minutes * 60
        + delta.seconds
    )


def _evaluate(node: dict[str, Any], lo: datetime, hi: datetime, tz: tzinfo) -> list[Interval]:
    """Evaluate a schedule node into interval list clipped to ``[lo, hi)``."""
    node_type = node.get("type")
    if node_type == "range":
        start = _parse_naive(node["start"]).replace(tzinfo=tz)
        end = _parse_naive(node["end"]).replace(tzinfo=tz)
        return _clip([(start, end)], lo, hi)
    if node_type == "period":
        return _clip(_period_intervals(node, lo, hi, tz), lo, hi)
    if node_type == "intersection":
        children = node.get("children", [])
        if not children:
            return []
        result = _evaluate(children[0], lo, hi, tz)
        for child in children[1:]:
            if not result:
                break
            result = _intersect_two(result, _evaluate(child, lo, hi, tz))
        return result
    if node_type == "union":
        merged: list[Interval] = []
        for child in node.get("children", []):
            merged.extend(_evaluate(child, lo, hi, tz))
        return _union(merged)
    if node_type == "difference":
        children = node.get("children", [])
        if not children:
            return []
        result = _evaluate(children[0], lo, hi, tz)
        for child in children[1:]:
            result = _subtract(result, _evaluate(child, lo, hi, tz))
        return result
    raise ValueError(f"Unknown schedule node type: {node_type!r}")


def expand(
    schedule: dict[str, Any],
    window_start: datetime,
    window_end: datetime,
    tz: tzinfo,
) -> list[Occurrence]:
    """Expand a schedule into occurrences overlapping ``[window_start, window_end)``.

    ``window_start``/``window_end`` may be tz-aware in any zone; they are
    converted into the schedule's zone (``tz``) for evaluation and the returned
    occurrences are tz-aware in ``tz``.
    """
    lo = window_start.astimezone(tz)
    hi = window_end.astimezone(tz)
    intervals = _evaluate(schedule, lo, hi, tz)
    intervals = _union(intervals) if intervals else intervals
    return [Occurrence(start=s, end=e) for s, e in sorted(intervals)]


def next_transition(
    schedule: dict[str, Any],
    at: datetime,
    tz: tzinfo,
    *,
    horizon: timedelta = timedelta(days=2),
) -> Occurrence | None:
    """Return the occurrence active at ``at`` or the next one within ``horizon``."""
    occurrences = expand(schedule, at - horizon, at + horizon, tz)
    at = at.astimezone(tz)
    for occ in occurrences:
        if occ.start <= at < occ.end or occ.start >= at:
            return occ
    return None
