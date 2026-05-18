"""Tests for UTE tariff calculator logic."""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from custom_components.ute_tarifas.const import ContractType, TariffPeriod
from custom_components.ute_tarifas.tariff import (
    PriceRange,
    ScheduleRange,
    TariffCalculator,
    TimeBlock,
    _active_price_range,
    _active_schedule_range,
    _contains,
    _next_occurrence,
    parse_blocks,
)

_UY = ZoneInfo("America/Montevideo")
_UTC = ZoneInfo("UTC")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _price_ranges() -> list[PriceRange]:
    return [
        PriceRange(
            start=date(2026, 1, 1),
            end=date(2026, 5, 31),
            simple_low=5.0,
            simple_mid=7.0,
            simple_high=9.0,
            double_llano=5.0,
            double_punta=9.0,
            triple_valle=4.0,
            triple_llano=6.0,
            triple_punta=10.0,
        ),
        PriceRange(
            start=date(2026, 6, 1),
            end=date(2026, 12, 31),
            simple_low=6.0,
            simple_mid=8.0,
            simple_high=10.0,
            double_llano=6.0,
            double_punta=11.0,
            triple_valle=5.0,
            triple_llano=7.0,
            triple_punta=12.0,
        ),
    ]


def _all_day_schedule(period: TariffPeriod) -> list[ScheduleRange]:
    """Single ScheduleRange covering all time with one all-day block."""
    block = [TimeBlock(time(0, 0), time(0, 0), period)]
    return [
        ScheduleRange(
            start=date.min,
            end=date.max,
            workday_blocks=block,
            weekend_blocks=block,
            holiday_blocks=block,
        )
    ]


def _make_schedule(
    workday_raw: str,
    weekend_raw: str = "00:00-00:00:valle",
    holiday_raw: str = "00:00-00:00:valle",
    *,
    dp: TariffPeriod = TariffPeriod.VALLE,
) -> list[ScheduleRange]:
    """Build a single eternal ScheduleRange from block strings."""
    return [
        ScheduleRange(
            start=date.min,
            end=date.max,
            workday_blocks=parse_blocks(workday_raw, default_period=dp),
            weekend_blocks=parse_blocks(weekend_raw, default_period=dp),
            holiday_blocks=parse_blocks(holiday_raw, default_period=dp),
        )
    ]


# ---------------------------------------------------------------------------
# parse_blocks
# ---------------------------------------------------------------------------


def test_parse_blocks_empty_string_returns_all_day_default() -> None:
    blocks = parse_blocks("", default_period=TariffPeriod.VALLE)
    assert len(blocks) == 1
    assert blocks[0].start == time(0, 0)
    assert blocks[0].end == time(0, 0)
    assert blocks[0].period == TariffPeriod.VALLE


def test_parse_blocks_whitespace_only_returns_all_day_default() -> None:
    blocks = parse_blocks("   ", default_period=TariffPeriod.LLANO)
    assert blocks[0].period == TariffPeriod.LLANO


def test_parse_blocks_parses_multiple_segments() -> None:
    blocks = parse_blocks(
        "00:00-07:00:valle,07:00-17:00:punta,17:00-00:00:valle",
        default_period=TariffPeriod.VALLE,
    )
    assert len(blocks) == 3
    assert blocks[0].period == TariffPeriod.VALLE
    assert blocks[1].period == TariffPeriod.PUNTA


def test_parse_blocks_rejects_bad_time_format() -> None:
    with pytest.raises(ValueError, match="Invalid time format"):
        parse_blocks("99-01:00:valle", default_period=TariffPeriod.VALLE)


def test_parse_blocks_rejects_invalid_period() -> None:
    with pytest.raises(ValueError):
        parse_blocks("00:00-07:00:unknown", default_period=TariffPeriod.VALLE)


def test_parse_blocks_rejects_bad_format() -> None:
    with pytest.raises(ValueError):
        parse_blocks("bad:format", default_period=TariffPeriod.VALLE)


# ---------------------------------------------------------------------------
# _contains
# ---------------------------------------------------------------------------


def test_contains_normal_block() -> None:
    block = TimeBlock(time(7, 0), time(17, 0), TariffPeriod.PUNTA)
    assert _contains(block, time(9, 0)) is True
    assert _contains(block, time(7, 0)) is True
    assert _contains(block, time(17, 0)) is False
    assert _contains(block, time(6, 59)) is False


def test_contains_midnight_wrap_block() -> None:
    block = TimeBlock(time(22, 0), time(0, 0), TariffPeriod.VALLE)
    assert _contains(block, time(23, 0)) is True
    assert _contains(block, time(22, 0)) is True
    assert _contains(block, time(0, 0)) is False
    assert _contains(block, time(21, 59)) is False


def test_contains_all_day_sentinel() -> None:
    block = TimeBlock(time(0, 0), time(0, 0), TariffPeriod.SIMPLE)
    for t in [time(0, 0), time(12, 0), time(23, 59)]:
        assert _contains(block, t) is True


# ---------------------------------------------------------------------------
# _next_occurrence
# ---------------------------------------------------------------------------


def test_next_occurrence_future_time() -> None:
    now = datetime(2026, 4, 10, 8, 0, tzinfo=_UY)
    result = _next_occurrence(now, time(22, 0))
    assert result == datetime(2026, 4, 10, 22, 0, tzinfo=_UY)


def test_next_occurrence_past_time_returns_next_day() -> None:
    now = datetime(2026, 4, 10, 23, 0, tzinfo=_UY)
    result = _next_occurrence(now, time(7, 0))
    assert result == datetime(2026, 4, 11, 7, 0, tzinfo=_UY)


def test_next_occurrence_midnight_target() -> None:
    now = datetime(2026, 4, 10, 22, 30, tzinfo=_UY)
    result = _next_occurrence(now, time(0, 0))
    assert result == datetime(2026, 4, 11, 0, 0, tzinfo=_UY)


# ---------------------------------------------------------------------------
# _active_price_range / _active_schedule_range
# ---------------------------------------------------------------------------


def test_active_price_range_found() -> None:
    pr = _active_price_range(date(2026, 3, 15), _price_ranges())
    assert pr.simple_mid == 7.0


def test_active_price_range_not_found_raises() -> None:
    with pytest.raises(ValueError, match="No active price range"):
        _active_price_range(date(2025, 1, 1), _price_ranges())


def test_active_schedule_range_found() -> None:
    ranges = _all_day_schedule(TariffPeriod.VALLE)
    sr = _active_schedule_range(date(2026, 4, 10), ranges)
    assert sr.workday_blocks[0].period == TariffPeriod.VALLE


def test_active_schedule_range_not_found_raises() -> None:
    ranges = [
        ScheduleRange(
            start=date(2027, 1, 1),
            end=date(2027, 12, 31),
            workday_blocks=[TimeBlock(time(0, 0), time(0, 0), TariffPeriod.VALLE)],
            weekend_blocks=[TimeBlock(time(0, 0), time(0, 0), TariffPeriod.VALLE)],
            holiday_blocks=[TimeBlock(time(0, 0), time(0, 0), TariffPeriod.VALLE)],
        )
    ]
    with pytest.raises(ValueError, match="No active schedule range"):
        _active_schedule_range(date(2026, 4, 10), ranges)


# ---------------------------------------------------------------------------
# TariffCalculator — SIMPLE contract
# ---------------------------------------------------------------------------


def test_simple_contract_returns_simple_period_and_cost() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
        monthly_kwh=350,  # mid tier
    )
    snap = calc.snapshot(datetime(2026, 4, 10, 18, 30, tzinfo=_UY))

    assert snap.current_period == TariffPeriod.SIMPLE
    assert snap.current_cost_excl_iva == 7.0  # simple_mid, monthly_kwh=350
    assert snap.next_period == TariffPeriod.SIMPLE
    assert snap.next_change_at == datetime(2026, 4, 11, 0, 0, tzinfo=_UY)


def test_simple_contract_next_change_is_price_range_start_if_sooner() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
    )
    snap = calc.snapshot(datetime(2026, 5, 31, 23, 0, tzinfo=_UY))

    assert snap.next_change_at == datetime(2026, 6, 1, 0, 0, tzinfo=_UY)
    assert snap.next_period == TariffPeriod.SIMPLE


def test_simple_contract_tier_selection() -> None:
    """monthly_kwh drives tier selection for the Simple contract."""
    pr = _price_ranges()

    low = TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=pr,
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
        monthly_kwh=80,
    )
    mid = TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=pr,
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
        monthly_kwh=350,
    )
    high = TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=pr,
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
        monthly_kwh=800,
    )

    ts = datetime(2026, 4, 10, 12, 0, tzinfo=_UY)
    assert low.snapshot(ts).current_cost_excl_iva == 5.0   # simple_low
    assert mid.snapshot(ts).current_cost_excl_iva == 7.0   # simple_mid
    assert high.snapshot(ts).current_cost_excl_iva == 9.0  # simple_high
    # Boundary at exactly 100 kWh → still low tier
    assert TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=pr,
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
        monthly_kwh=100,
    ).snapshot(ts).current_cost_excl_iva == 5.0
    # 101 kWh → mid tier
    assert TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=pr,
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
        monthly_kwh=101,
    ).snapshot(ts).current_cost_excl_iva == 7.0


# ---------------------------------------------------------------------------
# TariffCalculator — DOUBLE contract
# ---------------------------------------------------------------------------


def test_double_contract_uses_schedule_blocks() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-08:00:llano,08:00-22:00:punta,22:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
    )
    # 2026-04-06 is a Monday (workday), 09:00 → punta block
    snap = calc.snapshot(datetime(2026, 4, 6, 9, 0, tzinfo=_UY))

    assert snap.current_period == TariffPeriod.PUNTA
    assert snap.current_cost_excl_iva == 9.0
    assert snap.next_period == TariffPeriod.LLANO
    assert snap.next_change_at == datetime(2026, 4, 6, 22, 0, tzinfo=_UY)


def test_double_contract_weekend_is_all_llano() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-08:00:llano,08:00-22:00:punta,22:00-00:00:llano",
            weekend_raw="00:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
    )
    # 2026-04-11 is Saturday — all-llano
    snap = calc.snapshot(datetime(2026, 4, 11, 10, 0, tzinfo=_UY))
    assert snap.current_period == TariffPeriod.LLANO


def test_double_contract_uses_canonical_defaults() -> None:
    """Verify DEFAULT_DOUBLE_BLOCKS via prices.py are used when no custom schedule given."""
    from custom_components.ute_tarifas.prices import UTE_PRICE_RANGES, UTE_SCHEDULE_RANGES

    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=UTE_PRICE_RANGES,
        schedule_ranges=UTE_SCHEDULE_RANGES[ContractType.DOUBLE],
    )
    # 2026-04-06 is Monday (workday), 19:00 → punta in canonical DOUBLE schedule (18:00–22:00)
    snap = calc.snapshot(datetime(2026, 4, 6, 19, 0, tzinfo=_UY))
    assert snap.current_period == TariffPeriod.PUNTA


# ---------------------------------------------------------------------------
# TariffCalculator — TRIPLE contract
# ---------------------------------------------------------------------------


def test_triple_contract_detects_holiday_schedule() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            holiday_raw="00:00-00:00:valle",
            dp=TariffPeriod.LLANO,
        ),
    )
    # 2026-05-01 is a Uruguayan public holiday → holiday blocks (all-valle)
    snap = calc.snapshot(datetime(2026, 5, 1, 10, 0, tzinfo=_UY))

    assert snap.current_period == TariffPeriod.VALLE
    assert snap.current_cost_excl_iva == 4.0


def test_triple_contract_uses_canonical_defaults() -> None:
    """Verify DEFAULT_TRIPLE_BLOCKS via prices.py are used when no custom schedule given."""
    from custom_components.ute_tarifas.prices import UTE_PRICE_RANGES, UTE_SCHEDULE_RANGES

    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=UTE_PRICE_RANGES,
        schedule_ranges=UTE_SCHEDULE_RANGES[ContractType.TRIPLE],
    )
    # 2026-04-06 Monday 10:00 → llano in canonical TRIPLE schedule (07:00–18:00 is llano)
    snap = calc.snapshot(datetime(2026, 4, 6, 10, 0, tzinfo=_UY))
    assert snap.current_period == TariffPeriod.LLANO


def test_national_holidays_disabled() -> None:
    """With use_national_holidays=False a public holiday uses the workday schedule."""
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            holiday_raw="00:00-00:00:valle",
            dp=TariffPeriod.LLANO,
        ),
        use_national_holidays=False,
    )
    # 2026-05-01 would be a holiday but holidays are disabled → workday block at 10:00 = llano
    snap = calc.snapshot(datetime(2026, 5, 1, 10, 0, tzinfo=_UY))
    assert snap.current_period == TariffPeriod.LLANO


# ---------------------------------------------------------------------------
# next_change_at — price-range vs schedule-change ordering
# ---------------------------------------------------------------------------


def test_next_change_prefers_price_range_start_if_sooner() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-02:00:llano",
            weekend_raw="00:00-02:00:llano",
            dp=TariffPeriod.LLANO,
        ),
    )
    snap = calc.snapshot(datetime(2026, 5, 31, 23, 50, tzinfo=_UY))

    assert snap.next_change_at == datetime(2026, 6, 1, 0, 0, tzinfo=_UY)
    assert snap.next_period == TariffPeriod.LLANO


def test_next_tariff_data_change_returns_none_when_no_future_ranges() -> None:
    """_next_tariff_data_change returns None → snapshot uses schedule change instead."""
    single_range = [
        PriceRange(
            start=date(2026, 1, 1),
            end=date(2099, 12, 31),
            simple_low=5.0,
            simple_mid=7.0,
            simple_high=9.0,
            double_llano=5.0,
            double_punta=9.0,
            triple_valle=4.0,
            triple_llano=6.0,
            triple_punta=10.0,
        )
    ]
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=single_range,
        schedule_ranges=_make_schedule(
            "00:00-08:00:llano,08:00-22:00:punta,22:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
    )
    snap = calc.snapshot(datetime(2026, 4, 6, 9, 0, tzinfo=_UY))
    # No future price/schedule change → next_change_at is the schedule block boundary (22:00)
    assert snap.next_change_at == datetime(2026, 4, 6, 22, 0, tzinfo=_UY)


def test_next_change_prefers_schedule_boundary_if_sooner_than_price_change() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
    )
    # 2026-05-29 is a Friday (workday). At 20:00 the next block boundary is 21:00 (punta→llano).
    # June 1 price change is 25+ hours away → schedule boundary at 21:00 wins.
    snap = calc.snapshot(datetime(2026, 5, 29, 20, 0, tzinfo=_UY))
    assert snap.next_change_at == datetime(2026, 5, 29, 21, 0, tzinfo=_UY)


# ---------------------------------------------------------------------------
# ScheduleRange date-bounded transitions
# ---------------------------------------------------------------------------


def test_schedule_range_transition_on_boundary_date() -> None:
    """Verify that the correct ScheduleRange is selected on the exact transition date."""
    old_block = [TimeBlock(time(0, 0), time(0, 0), TariffPeriod.PUNTA)]
    new_block = [TimeBlock(time(0, 0), time(0, 0), TariffPeriod.VALLE)]
    schedule_ranges = [
        ScheduleRange(
            start=date(2026, 1, 1),
            end=date(2026, 6, 30),
            workday_blocks=old_block,
            weekend_blocks=old_block,
            holiday_blocks=old_block,
        ),
        ScheduleRange(
            start=date(2026, 7, 1),
            end=date(2099, 12, 31),
            workday_blocks=new_block,
            weekend_blocks=new_block,
            holiday_blocks=new_block,
        ),
    ]
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        schedule_ranges=schedule_ranges,
    )

    snap_before = calc.snapshot(datetime(2026, 6, 30, 12, 0, tzinfo=_UY))
    assert snap_before.current_period == TariffPeriod.PUNTA

    # On 2026-07-01, the new schedule applies immediately
    # Note: 2026-07-01 price range end is 2026-12-31; price is still valid
    # We need to use a price range that covers July
    calc2 = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=[
            PriceRange(
                start=date(2026, 1, 1),
                end=date(2099, 12, 31),
                simple_low=5.0,
                simple_mid=7.0,
                simple_high=9.0,
                double_llano=5.0,
                double_punta=9.0,
                triple_valle=4.0,
                triple_llano=6.0,
                triple_punta=10.0,
            )
        ],
        schedule_ranges=schedule_ranges,
    )
    snap_after = calc2.snapshot(datetime(2026, 7, 1, 12, 0, tzinfo=_UY))
    assert snap_after.current_period == TariffPeriod.VALLE


def test_next_change_at_reports_upcoming_schedule_range_start() -> None:
    """next_change_at skips non-real boundaries and surfaces the next actual period change.

    With the scan-forward fix, the calculator skips midnight June 30 (same PUNTA period
    continues) and directly reports the ScheduleRange transition at July 1 00:00 where the
    period changes from PUNTA to VALLE.
    """
    current_block = [TimeBlock(time(0, 0), time(0, 0), TariffPeriod.PUNTA)]
    future_block = [TimeBlock(time(0, 0), time(0, 0), TariffPeriod.VALLE)]
    schedule_ranges = [
        ScheduleRange(
            start=date(2026, 1, 1),
            end=date(2026, 6, 30),
            workday_blocks=current_block,
            weekend_blocks=current_block,
            holiday_blocks=current_block,
        ),
        ScheduleRange(
            start=date(2026, 7, 1),
            end=date(2099, 12, 31),
            workday_blocks=future_block,
            weekend_blocks=future_block,
            holiday_blocks=future_block,
        ),
    ]
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=[
            PriceRange(
                start=date(2026, 1, 1),
                end=date(2099, 12, 31),
                simple_low=5.0,
                simple_mid=7.0,
                simple_high=9.0,
                double_llano=5.0,
                double_punta=9.0,
                triple_valle=4.0,
                triple_llano=6.0,
                triple_punta=10.0,
            )
        ],
        schedule_ranges=schedule_ranges,
    )
    snap = calc.snapshot(datetime(2026, 6, 29, 12, 0, tzinfo=_UY))
    # Scan-forward skips the non-real June 30 midnight boundary (still PUNTA) and
    # directly reports the ScheduleRange transition at July 1 00:00 (PUNTA → VALLE).
    assert snap.next_change_at == datetime(2026, 7, 1, 0, 0, tzinfo=_UY)
    assert snap.next_period == TariffPeriod.VALLE


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_raises_without_active_price_range() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=[
            PriceRange(
                start=date(2026, 1, 1),
                end=date(2026, 1, 31),
                simple_low=5.0,
                simple_mid=7.0,
                simple_high=9.0,
                double_llano=5.0,
                double_punta=9.0,
                triple_valle=4.0,
                triple_llano=6.0,
                triple_punta=10.0,
            )
        ],
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
    )

    with pytest.raises(ValueError, match="No active price range"):
        calc.snapshot(datetime(2026, 2, 1, 0, 1, tzinfo=_UY))


def test_raises_without_active_schedule_range() -> None:
    # DOUBLE contract calls _blocks_for_day → _active_schedule_range; SIMPLE short-circuits.
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        schedule_ranges=[
            ScheduleRange(
                start=date(2027, 1, 1),
                end=date(2027, 12, 31),
                workday_blocks=[TimeBlock(time(0, 0), time(0, 0), TariffPeriod.SIMPLE)],
                weekend_blocks=[TimeBlock(time(0, 0), time(0, 0), TariffPeriod.SIMPLE)],
                holiday_blocks=[TimeBlock(time(0, 0), time(0, 0), TariffPeriod.SIMPLE)],
            )
        ],
    )

    with pytest.raises(ValueError, match="No active schedule range"):
        calc.snapshot(datetime(2026, 4, 10, 10, 0, tzinfo=_UY))


# ---------------------------------------------------------------------------
# Timezone correctness: snapshot must use UY wall-clock time
# ---------------------------------------------------------------------------


def test_utc_datetime_near_midnight_resolves_using_uy_date() -> None:
    """01:00 UTC on a Tuesday is 22:00 Monday in UY (UTC-3).

    A double-tariff calculator with a punta block 08:00-22:00 on workdays
    should report LLANO at 22:00 UY (Monday evening), not look at Tuesday.
    With the scan-forward fix, the next real change is Tuesday 08:00 when PUNTA
    starts — not midnight (where the same LLANO period continues on Tuesday).
    """
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-08:00:llano,08:00-22:00:punta,22:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
    )

    # 2026-04-07 01:00 UTC  ==  2026-04-06 22:00 UY (Monday evening, workday)
    snap = calc.snapshot(datetime(2026, 4, 7, 1, 0, tzinfo=_UTC))

    assert snap.current_period == TariffPeriod.LLANO
    # Scan-forward skips midnight (LLANO continues on Tuesday 00:00–08:00)
    # and returns the next REAL change: Tuesday 08:00 when PUNTA starts.
    assert snap.next_change_at == datetime(2026, 4, 7, 8, 0, tzinfo=_UY)
    assert snap.next_period == TariffPeriod.PUNTA


def test_utc_datetime_determines_holiday_in_uy_calendar() -> None:
    """23:30 UTC on April 30 is 20:30 UY on April 30 — NOT May 1 yet.

    May 1 is a Uruguayan public holiday.  A triple-tariff calculator
    should use the workday schedule for April 30 UY (20:30 is punta),
    and the holiday schedule once the clock crosses midnight in UY.
    """
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            holiday_raw="00:00-00:00:valle",
            dp=TariffPeriod.LLANO,
        ),
    )

    # 2026-04-30 23:30 UTC  ==  2026-04-30 20:30 UY (still April 30, workday punta)
    snap = calc.snapshot(datetime(2026, 4, 30, 23, 30, tzinfo=_UTC))
    assert snap.current_period == TariffPeriod.PUNTA

    # 2026-05-01 03:00 UTC  ==  2026-05-01 00:00 UY (May 1, national holiday → valle)
    snap_holiday = calc.snapshot(datetime(2026, 5, 1, 3, 0, tzinfo=_UTC))
    assert snap_holiday.current_period == TariffPeriod.VALLE


# ---------------------------------------------------------------------------
# IVA calculation
# ---------------------------------------------------------------------------


def test_snapshot_includes_iva_in_current_cost() -> None:
    """current_cost must be current_cost_excl_iva * (1 + iva_rate)."""
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
        iva_rate=0.22,
    )
    snap = calc.snapshot(datetime(2026, 4, 6, 10, 0, tzinfo=_UY))  # Monday 10:00 → llano
    assert snap.iva_rate == 0.22
    assert snap.current_cost_excl_iva == 6.0  # triple_llano from first price range
    assert abs(snap.current_cost - 6.0 * 1.22) < 1e-9


def test_snapshot_iva_rate_zero_means_no_markup() -> None:
    """iva_rate=0 makes current_cost equal to current_cost_excl_iva."""
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-08:00:llano,08:00-22:00:punta,22:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
        iva_rate=0.0,
    )
    snap = calc.snapshot(datetime(2026, 4, 6, 9, 0, tzinfo=_UY))  # Monday 09:00 → punta
    assert snap.current_cost_excl_iva == 9.0
    assert snap.current_cost == 9.0


# ---------------------------------------------------------------------------
# _next_schedule_change — weekend-to-workday transition
# ---------------------------------------------------------------------------


def test_next_change_skips_same_period_weekend_boundaries() -> None:
    """Saturday→Sunday boundary must be skipped; next REAL change is Monday 00:00 (TRIPLE).

    In a TRIPLE contract, both Saturday and Sunday are all-valle.  The scan-forward
    fix should skip the Saturday midnight boundary (still valle on Sunday) and return
    Monday 00:00 when the first workday block (LLANO) starts.
    """
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            weekend_raw="00:00-00:00:valle",
            dp=TariffPeriod.LLANO,
        ),
    )
    # 2026-04-11 is Saturday at 15:00 → all-valle
    snap = calc.snapshot(datetime(2026, 4, 11, 15, 0, tzinfo=_UY))
    assert snap.current_period == TariffPeriod.VALLE
    # Skip Saturday midnight (Sunday is also all-valle), then skip Sunday midnight
    # (Monday 00:00–07:00 is also VALLE per workday blocks).
    # Next REAL change: Monday 07:00 when LLANO starts.
    assert snap.next_change_at == datetime(2026, 4, 13, 7, 0, tzinfo=_UY)
    assert snap.next_period == TariffPeriod.LLANO


def test_next_change_double_weekend_to_workday() -> None:
    """DOUBLE: Saturday all-llano should skip Sunday; next change at Monday 07:00 → PUNTA."""
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-07:00:llano,07:00-17:00:punta,17:00-00:00:llano",
            weekend_raw="00:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
    )
    # 2026-04-12 is Sunday at 20:00 → all-llano
    snap = calc.snapshot(datetime(2026, 4, 12, 20, 0, tzinfo=_UY))
    assert snap.current_period == TariffPeriod.LLANO
    # Sunday midnight → Monday 00:00–07:00 still LLANO → skip to Monday 07:00 → PUNTA
    assert snap.next_change_at == datetime(2026, 4, 13, 7, 0, tzinfo=_UY)
    assert snap.next_period == TariffPeriod.PUNTA


# ---------------------------------------------------------------------------
# _is_holiday — error handling with invalid country code
# ---------------------------------------------------------------------------


def test_is_holiday_invalid_country_returns_false(caplog: pytest.LogCaptureFixture) -> None:
    """An invalid country code must not raise; _is_holiday returns False and logs a warning."""
    import logging

    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        schedule_ranges=_make_schedule(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            holiday_raw="00:00-00:00:valle",
            dp=TariffPeriod.LLANO,
        ),
        country="XX",  # not a valid holidays country code
        use_national_holidays=True,
    )

    with caplog.at_level(logging.WARNING, logger="custom_components.ute_tarifas.tariff"):
        # 2026-05-01 would normally be a holiday in UY; with bad country code it's treated
        # as a non-holiday → workday blocks apply → 10:00 should be llano
        snap = calc.snapshot(datetime(2026, 5, 1, 10, 0, tzinfo=_UY))

    assert snap.current_period == TariffPeriod.LLANO
    assert any("XX" in message for message in caplog.messages)


# ---------------------------------------------------------------------------
# active_price_range — all tier prices in snapshot
# ---------------------------------------------------------------------------


def test_snapshot_includes_active_price_range() -> None:
    """TariffSnapshot.active_price_range exposes every tier price from prices.py."""
    pr = _price_ranges()
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=pr,
        schedule_ranges=_make_schedule(
            "00:00-08:00:llano,08:00-22:00:punta,22:00-00:00:llano",
            dp=TariffPeriod.LLANO,
        ),
    )
    snap = calc.snapshot(datetime(2026, 4, 6, 9, 0, tzinfo=_UY))

    # The active price range is the first entry (Jan–May 2026)
    assert snap.active_price_range.simple_low == 5.0
    assert snap.active_price_range.simple_mid == 7.0
    assert snap.active_price_range.simple_high == 9.0
    assert snap.active_price_range.double_llano == 5.0
    assert snap.active_price_range.double_punta == 9.0
    assert snap.active_price_range.triple_valle == 4.0
    assert snap.active_price_range.triple_llano == 6.0
    assert snap.active_price_range.triple_punta == 10.0


def test_monthly_kwh_setter_updates_simple_tier() -> None:
    """TariffCalculator.monthly_kwh setter changes the Simple tier at runtime."""
    pr = _price_ranges()
    calc = TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=pr,
        schedule_ranges=_all_day_schedule(TariffPeriod.SIMPLE),
        monthly_kwh=0,
    )
    ts = datetime(2026, 4, 10, 12, 0, tzinfo=_UY)

    # Default: 0 kWh → simple_low
    assert calc.snapshot(ts).current_cost_excl_iva == 5.0

    # Update to mid tier
    calc.monthly_kwh = 350
    assert calc.snapshot(ts).current_cost_excl_iva == 7.0

    # Update to high tier
    calc.monthly_kwh = 700
    assert calc.snapshot(ts).current_cost_excl_iva == 9.0
