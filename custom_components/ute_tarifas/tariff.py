"""Tariff calculation primitives for UTE residential plans."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import holidays

from .const import ContractType, TariffPeriod

_LOGGER = logging.getLogger(__name__)

# All schedule and holiday comparisons are performed in UY local time.
# UTE tariff periods are defined by wall-clock hours in Uruguay, so any
# datetime passed from the outside (which may carry a different timezone,
# e.g. UTC when Home Assistant runs on a non-UY server) is converted to
# this timezone before any date or time comparison is made.
UY_TZ = ZoneInfo("America/Montevideo")


@dataclass(frozen=True)
class TimeBlock:
    """A time-of-use block in local wall-clock time.

    ``end=time(0, 0)`` is the sentinel value for "until midnight".  When
    ``start >= end`` (including the all-day ``00:00–00:00`` case) the block
    wraps around midnight — see :func:`_contains`.
    """

    start: time
    end: time
    period: TariffPeriod


@dataclass(frozen=True)
class ScheduleRange:
    """Schedule (time-of-use blocks per day type) valid within a date interval.

    To encode a future schedule change, add a new entry (and close the previous
    one) in ``prices.py``.  Both changes take effect automatically on the
    specified date — no HA restart or user action is needed.
    """

    start: date
    end: date
    workday_blocks: list[TimeBlock]
    weekend_blocks: list[TimeBlock]
    holiday_blocks: list[TimeBlock]


@dataclass(frozen=True)
class PriceRange:
    """Price set (UYU/kWh per period) valid within a date interval.

    To update prices, add a new entry to ``UTE_PRICE_RANGES`` in
    ``prices.py`` and close the previous one.
    """

    start: date
    end: date
    simple: float
    double_valle: float
    double_punta: float
    triple_valle: float
    triple_llano: float
    triple_punta: float


@dataclass(frozen=True)
class TariffSnapshot:
    """Point-in-time tariff result returned by :meth:`TariffCalculator.snapshot`."""

    current_period: TariffPeriod
    current_cost: float
    next_change_at: datetime
    next_period: TariffPeriod


def _parse_time(value: str) -> time:
    """Parse ``"HH:MM"`` into a :class:`datetime.time`.

    Raises :exc:`ValueError` if the format is invalid.
    """
    parts = value.split(":", maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {value!r}")
    try:
        return time(hour=int(parts[0]), minute=int(parts[1]))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid time value: {value!r}") from exc


def parse_blocks(raw: str, *, default_period: TariffPeriod) -> list[TimeBlock]:
    """Parse a schedule string into a list of :class:`TimeBlock` objects.

    Format::

        "HH:MM-HH:MM:period,HH:MM-HH:MM:period"

    Valid period names: ``valle``, ``llano``, ``punta``, ``simple``.

    An empty *raw* string returns a single all-day block using
    *default_period*.  ``end=time(0, 0)`` is the "until midnight" sentinel
    handled by the wrap-around logic in :func:`_contains`.
    """
    if not raw.strip():
        return [TimeBlock(time(0, 0), time(0, 0), default_period)]

    blocks: list[TimeBlock] = []
    for segment in raw.split(","):
        segment = segment.strip()
        if not segment:
            continue
        window, period_raw = segment.rsplit(":", maxsplit=1)
        start_raw, end_raw = window.split("-", maxsplit=1)
        blocks.append(
            TimeBlock(
                start=_parse_time(start_raw.strip()),
                end=_parse_time(end_raw.strip()),
                period=TariffPeriod(period_raw.strip()),
            )
        )

    if not blocks:
        raise ValueError("Schedule must contain at least one block")

    return blocks


def _contains(block: TimeBlock, current: time) -> bool:
    """Return ``True`` if *current* falls within *block*'s time window.

    When ``block.start >= block.end`` (e.g. ``22:00–00:00`` or the all-day
    sentinel ``00:00–00:00``) the block wraps around midnight.
    """
    if block.start < block.end:
        return block.start <= current < block.end
    # Wrap-around: covers [start, midnight) ∪ [midnight, end)
    return current >= block.start or current < block.end


def _next_occurrence(now: datetime, target: time) -> datetime:
    """Return the next wall-clock moment *target* occurs strictly after *now*."""
    candidate = datetime.combine(now.date(), target, tzinfo=now.tzinfo)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _active_price_range(current_date: date, price_ranges: list[PriceRange]) -> PriceRange:
    """Return the :class:`PriceRange` covering *current_date*.

    Raises :exc:`ValueError` if no range covers the date.
    """
    for price in price_ranges:
        if price.start <= current_date <= price.end:
            return price
    raise ValueError(f"No active price range for {current_date}")


def _active_schedule_range(
    current_date: date, schedule_ranges: list[ScheduleRange]
) -> ScheduleRange:
    """Return the :class:`ScheduleRange` covering *current_date*.

    Raises :exc:`ValueError` if no range covers the date.
    """
    for sched in schedule_ranges:
        if sched.start <= current_date <= sched.end:
            return sched
    raise ValueError(f"No active schedule range for {current_date}")


def _first_block(blocks: list[TimeBlock]) -> TimeBlock:
    """Return the block with the earliest start time (used as a day-start fallback)."""
    return min(blocks, key=lambda b: (b.start.hour, b.start.minute, b.start.second))


class TariffCalculator:
    """Computes the residential UTE tariff state for a given moment in time.

    All public entry points accept any timezone-aware :class:`~datetime.datetime`.
    Internally everything is converted to ``America/Montevideo`` (``UY_TZ``)
    before any date/time comparison so that schedule blocks and holidays are
    always evaluated against the correct UY wall-clock time, regardless of the
    timezone configured on the Home Assistant server.

    Pricing and schedule data are maintained in ``prices.py``.  Future changes
    (new tariff rates, new time-of-use hours) are encoded there with effective
    date ranges and take effect automatically — no coordinator restart needed.
    """

    def __init__(
        self,
        *,
        contract_type: ContractType,
        price_ranges: list[PriceRange],
        schedule_ranges: list[ScheduleRange],
        country: str = "UY",
        use_national_holidays: bool = True,
    ) -> None:
        self._contract_type = contract_type
        self._price_ranges = sorted(price_ranges, key=lambda p: p.start)
        self._schedule_ranges = sorted(schedule_ranges, key=lambda s: s.start)
        self._country = country
        self._use_national_holidays = use_national_holidays
        # Cache holiday sets keyed by (country, year) to avoid reconstructing
        # the holidays object on every _is_holiday() call within a snapshot().
        self._holiday_cache: dict[tuple[str, int], frozenset[date]] = {}

    def _is_holiday(self, value: date) -> bool:
        if not self._use_national_holidays:
            return False
        key = (self._country, value.year)
        if key not in self._holiday_cache:
            try:
                self._holiday_cache[key] = frozenset(
                    holidays.country_holidays(self._country, years=value.year).keys()
                )
            except (KeyError, NotImplementedError) as exc:
                _LOGGER.warning(
                    "Holiday lookup failed for country %r on %s: %s — treating as non-holiday",
                    self._country,
                    value,
                    exc,
                )
                self._holiday_cache[key] = frozenset()
        return value in self._holiday_cache[key]

    def _blocks_for_day(self, value: date) -> list[TimeBlock]:
        sched = _active_schedule_range(value, self._schedule_ranges)
        if self._is_holiday(value):
            return sched.holiday_blocks
        if value.weekday() >= 5:  # Saturday=5, Sunday=6
            return sched.weekend_blocks
        return sched.workday_blocks

    def _period_for_datetime(self, value: datetime) -> TariffPeriod:
        if self._contract_type == ContractType.SIMPLE:
            return TariffPeriod.SIMPLE

        blocks = self._blocks_for_day(value.date())
        current = value.timetz().replace(tzinfo=None)
        for block in blocks:
            if _contains(block, current):
                return block.period

        return _first_block(blocks).period

    def _price_for_period(self, period: TariffPeriod, price: PriceRange) -> float:
        if self._contract_type == ContractType.SIMPLE:
            return price.simple
        if self._contract_type == ContractType.DOUBLE:
            return price.double_punta if period == TariffPeriod.PUNTA else price.double_valle
        if period == TariffPeriod.VALLE:
            return price.triple_valle
        if period == TariffPeriod.PUNTA:
            return price.triple_punta
        return price.triple_llano

    def _next_schedule_change(self, now: datetime) -> tuple[datetime, TariffPeriod]:
        if self._contract_type == ContractType.SIMPLE:
            tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return tomorrow, TariffPeriod.SIMPLE

        blocks = self._blocks_for_day(now.date())
        candidates: list[tuple[datetime, TariffPeriod]] = [
            (_next_occurrence(now, block.end), block.period) for block in blocks
        ]
        next_change_at, _ = min(candidates, key=lambda item: item[0])
        next_period = self._period_for_datetime(next_change_at + timedelta(seconds=1))
        return next_change_at, next_period

    def _next_tariff_data_change(self, now: datetime) -> datetime | None:
        """Return the soonest future datetime when either prices or the schedule changes.

        Both :attr:`price_ranges` and :attr:`schedule_ranges` can encode future
        effective dates via their ``start`` field.  This method finds the
        earliest such date so the ``next_change_at`` sensor reflects upcoming
        pricing or schedule transitions before they happen.
        """
        candidates: list[datetime] = []
        for price in self._price_ranges:
            if price.start > now.date():
                candidates.append(datetime.combine(price.start, time(0, 0), tzinfo=now.tzinfo))
        for sched in self._schedule_ranges:
            if sched.start > now.date():
                candidates.append(datetime.combine(sched.start, time(0, 0), tzinfo=now.tzinfo))
        return min(candidates) if candidates else None

    def snapshot(self, now: datetime) -> TariffSnapshot:
        """Return the tariff state at *now*.

        *now* may carry any timezone.  It is converted to UY local time
        (``America/Montevideo``) first so that schedule blocks, holiday
        detection, and date-range comparisons all use the correct UY
        calendar date and wall-clock hour — regardless of the timezone
        configured on the Home Assistant server.
        """
        now = now.astimezone(UY_TZ)
        period = self._period_for_datetime(now)
        active_price = _active_price_range(now.date(), self._price_ranges)
        cost = self._price_for_period(period, active_price)

        schedule_change_at, schedule_next_period = self._next_schedule_change(now)
        next_tariff_data_change = self._next_tariff_data_change(now)

        if next_tariff_data_change is not None and next_tariff_data_change < schedule_change_at:
            next_period = self._period_for_datetime(next_tariff_data_change + timedelta(seconds=1))
            return TariffSnapshot(
                current_period=period,
                current_cost=cost,
                next_change_at=next_tariff_data_change,
                next_period=next_period,
            )

        return TariffSnapshot(
            current_period=period,
            current_cost=cost,
            next_change_at=schedule_change_at,
            next_period=schedule_next_period,
        )
