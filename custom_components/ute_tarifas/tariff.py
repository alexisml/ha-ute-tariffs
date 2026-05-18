"""Tariff calculation primitives for UTE residential plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import holidays

from .const import ContractType, TariffPeriod


@dataclass(frozen=True)
class TimeBlock:
    """A period block in local wall-clock time."""

    start: time
    end: time
    period: TariffPeriod


@dataclass(frozen=True)
class PriceRange:
    """Price set valid in a date interval."""

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
    """Current tariff result payload."""

    current_period: TariffPeriod
    current_cost: float
    next_change_at: datetime
    next_period: TariffPeriod


DEFAULT_DOUBLE_BLOCKS = [
    TimeBlock(time(0, 0), time(7, 0), TariffPeriod.VALLE),
    TimeBlock(time(7, 0), time(17, 0), TariffPeriod.PUNTA),
    # end=time(0,0) represents midnight (start of the next day) via _contains wrap-around logic
    TimeBlock(time(17, 0), time(0, 0), TariffPeriod.VALLE),
]

DEFAULT_TRIPLE_BLOCKS = [
    TimeBlock(time(0, 0), time(7, 0), TariffPeriod.VALLE),
    TimeBlock(time(7, 0), time(17, 0), TariffPeriod.LLANO),
    TimeBlock(time(17, 0), time(21, 0), TariffPeriod.PUNTA),
    # end=time(0,0) represents midnight (start of the next day) via _contains wrap-around logic
    TimeBlock(time(21, 0), time(0, 0), TariffPeriod.LLANO),
]


def _parse_time(value: str) -> time:
    parts = value.split(":", maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {value}")
    return time(hour=int(parts[0]), minute=int(parts[1]))


def parse_blocks(raw: str, *, default_period: TariffPeriod) -> list[TimeBlock]:
    """Parse schedule text into blocks.

    Format: "HH:MM-HH:MM:period,HH:MM-HH:MM:period"
    Period names: valle, llano, punta, simple.
    """
    if not raw.strip():
        return [TimeBlock(time(0, 0), time(23, 59, 59), default_period)]

    blocks: list[TimeBlock] = []
    for block in raw.split(","):
        window, period_raw = block.strip().rsplit(":", maxsplit=1)
        start_raw, end_raw = window.split("-", maxsplit=1)
        blocks.append(
            TimeBlock(
                start=_parse_time(start_raw.strip()),
                end=_parse_time(end_raw.strip()),
                period=TariffPeriod(period_raw.strip()),
            )
        )

    if not blocks:
        raise ValueError("At least one block is required")

    return blocks


def _contains(block: TimeBlock, current: time) -> bool:
    if block.start < block.end:
        return block.start <= current < block.end
    return current >= block.start or current < block.end


def _next_occurrence(now: datetime, target: time) -> datetime:
    candidate = datetime.combine(now.date(), target, tzinfo=now.tzinfo)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _active_price_range(current_date: date, price_ranges: list[PriceRange]) -> PriceRange:
    for price in price_ranges:
        if price.start <= current_date <= price.end:
            return price
    raise ValueError("No active price range for current date")


def _first_block(blocks: list[TimeBlock]) -> TimeBlock:
    return min(blocks, key=lambda b: (b.start.hour, b.start.minute, b.start.second))


class TariffCalculator:
    """Computes residential UTE tariff state."""

    def __init__(
        self,
        *,
        contract_type: ContractType,
        price_ranges: list[PriceRange],
        workday_blocks: list[TimeBlock] | None = None,
        weekend_blocks: list[TimeBlock] | None = None,
        holiday_blocks: list[TimeBlock] | None = None,
        country: str = "UY",
        use_national_holidays: bool = True,
    ) -> None:
        self._contract_type = contract_type
        self._price_ranges = sorted(price_ranges, key=lambda p: p.start)
        self._workday_blocks = workday_blocks or self._default_blocks()
        self._weekend_blocks = weekend_blocks or self._default_blocks()
        self._holiday_blocks = holiday_blocks or self._default_blocks()
        self._country = country
        self._use_national_holidays = use_national_holidays

    def _default_blocks(self) -> list[TimeBlock]:
        if self._contract_type == ContractType.SIMPLE:
            return [TimeBlock(time(0, 0), time(23, 59, 59), TariffPeriod.SIMPLE)]
        if self._contract_type == ContractType.DOUBLE:
            return DEFAULT_DOUBLE_BLOCKS
        return DEFAULT_TRIPLE_BLOCKS

    def _is_holiday(self, value: date) -> bool:
        if not self._use_national_holidays:
            return False
        years = {value.year, (value + timedelta(days=1)).year}
        return value in holidays.country_holidays(self._country, years=years)

    def _blocks_for_day(self, value: date) -> list[TimeBlock]:
        if self._is_holiday(value):
            return self._holiday_blocks
        if value.weekday() >= 5:
            return self._weekend_blocks
        return self._workday_blocks

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
            if period == TariffPeriod.PUNTA:
                return price.double_punta
            return price.double_valle

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
        candidates: list[tuple[datetime, TariffPeriod]] = []
        for block in blocks:
            candidates.append((_next_occurrence(now, block.end), block.period))

        next_change_at, _ = min(candidates, key=lambda item: item[0])
        next_period = self._period_for_datetime(next_change_at + timedelta(seconds=1))
        return next_change_at, next_period

    def _next_price_change(self, now: datetime) -> datetime | None:
        for price in self._price_ranges:
            if price.start > now.date():
                return datetime.combine(price.start, time(0, 0), tzinfo=now.tzinfo)
        return None

    def snapshot(self, now: datetime) -> TariffSnapshot:
        period = self._period_for_datetime(now)
        active_price = _active_price_range(now.date(), self._price_ranges)
        cost = self._price_for_period(period, active_price)

        schedule_change_at, schedule_next_period = self._next_schedule_change(now)
        next_price_change = self._next_price_change(now)

        if next_price_change is not None and next_price_change < schedule_change_at:
            next_period = self._period_for_datetime(next_price_change + timedelta(seconds=1))
            return TariffSnapshot(
                current_period=period,
                current_cost=cost,
                next_change_at=next_price_change,
                next_period=next_period,
            )

        return TariffSnapshot(
            current_period=period,
            current_cost=cost,
            next_change_at=schedule_change_at,
            next_period=schedule_next_period,
        )
