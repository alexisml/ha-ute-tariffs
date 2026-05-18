"""Tests for UTE tariff calculator logic."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.ute_tarifas.const import ContractType, TariffPeriod
from custom_components.ute_tarifas.tariff import PriceRange, TariffCalculator, parse_blocks


def _price_ranges() -> list[PriceRange]:
    return [
        PriceRange(
            start=date(2026, 1, 1),
            end=date(2026, 5, 31),
            simple=7.0,
            double_valle=5.0,
            double_punta=9.0,
            triple_valle=4.0,
            triple_llano=6.0,
            triple_punta=10.0,
        ),
        PriceRange(
            start=date(2026, 6, 1),
            end=date(2026, 12, 31),
            simple=8.0,
            double_valle=6.0,
            double_punta=11.0,
            triple_valle=5.0,
            triple_llano=7.0,
            triple_punta=12.0,
        ),
    ]


def test_simple_contract_returns_simple_period_and_cost() -> None:
    calc = TariffCalculator(contract_type=ContractType.SIMPLE, price_ranges=_price_ranges())
    snap = calc.snapshot(datetime(2026, 4, 10, 18, 30, tzinfo=ZoneInfo("America/Montevideo")))

    assert snap.current_period == TariffPeriod.SIMPLE
    assert snap.current_cost == 7.0
    assert snap.next_period == TariffPeriod.SIMPLE
    assert snap.next_change_at == datetime(
        2026, 4, 11, 0, 0, tzinfo=ZoneInfo("America/Montevideo")
    )


def test_double_contract_uses_schedule_blocks() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        workday_blocks=parse_blocks(
            "00:00-08:00:valle,08:00-22:00:punta,22:00-00:00:valle",
            default_period=TariffPeriod.VALLE,
        ),
        weekend_blocks=parse_blocks("00:00-00:00:valle", default_period=TariffPeriod.VALLE),
        holiday_blocks=parse_blocks("00:00-00:00:valle", default_period=TariffPeriod.VALLE),
    )
    snap = calc.snapshot(datetime(2026, 4, 6, 9, 0, tzinfo=ZoneInfo("America/Montevideo")))

    assert snap.current_period == TariffPeriod.PUNTA
    assert snap.current_cost == 9.0
    assert snap.next_period == TariffPeriod.VALLE
    assert snap.next_change_at == datetime(
        2026, 4, 6, 22, 0, tzinfo=ZoneInfo("America/Montevideo")
    )


def test_triple_contract_detects_holiday_schedule() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        workday_blocks=parse_blocks(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            default_period=TariffPeriod.LLANO,
        ),
        holiday_blocks=parse_blocks("00:00-00:00:valle", default_period=TariffPeriod.VALLE),
    )
    snap = calc.snapshot(datetime(2026, 5, 1, 10, 0, tzinfo=ZoneInfo("America/Montevideo")))

    assert snap.current_period == TariffPeriod.VALLE
    assert snap.current_cost == 4.0


def test_next_change_prefers_price_range_start_if_sooner() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        workday_blocks=parse_blocks("00:00-02:00:llano", default_period=TariffPeriod.LLANO),
        weekend_blocks=parse_blocks("00:00-02:00:llano", default_period=TariffPeriod.LLANO),
    )
    snap = calc.snapshot(datetime(2026, 5, 31, 23, 50, tzinfo=ZoneInfo("America/Montevideo")))

    assert snap.next_change_at == datetime(
        2026, 6, 1, 0, 0, tzinfo=ZoneInfo("America/Montevideo")
    )
    assert snap.next_period == TariffPeriod.LLANO


def test_raises_without_active_price_range() -> None:
    calc = TariffCalculator(
        contract_type=ContractType.SIMPLE,
        price_ranges=[
            PriceRange(
                start=date(2026, 1, 1),
                end=date(2026, 1, 31),
                simple=7.0,
                double_valle=5.0,
                double_punta=9.0,
                triple_valle=4.0,
                triple_llano=6.0,
                triple_punta=10.0,
            )
        ],
    )

    with pytest.raises(ValueError, match="No active price range"):
        calc.snapshot(datetime(2026, 2, 1, 0, 1, tzinfo=ZoneInfo("America/Montevideo")))


def test_parse_blocks_rejects_invalid_time() -> None:
    with pytest.raises(ValueError):
        parse_blocks("bad:format", default_period=TariffPeriod.VALLE)


# ---------------------------------------------------------------------------
# Timezone correctness: the snapshot must always resolve using UY wall-clock
# ---------------------------------------------------------------------------

_UTC = ZoneInfo("UTC")
_UY = ZoneInfo("America/Montevideo")


def test_utc_datetime_near_midnight_resolves_using_uy_date() -> None:
    """01:00 UTC on a Tuesday is 22:00 Monday in UY (UTC-3).

    A double-tariff calculator with a punta block 08:00-22:00 on workdays
    should report PUNTA when given 09:00 UY, but VALLE at 22:00 UY.
    At 01:00 UTC (= 22:00 UY on the previous calendar day) the block
    22:00-00:00 VALLE should be active, not Tuesday's early-morning block.
    """
    calc = TariffCalculator(
        contract_type=ContractType.DOUBLE,
        price_ranges=_price_ranges(),
        workday_blocks=parse_blocks(
            "00:00-08:00:valle,08:00-22:00:punta,22:00-00:00:valle",
            default_period=TariffPeriod.VALLE,
        ),
        weekend_blocks=parse_blocks("00:00-00:00:valle", default_period=TariffPeriod.VALLE),
        holiday_blocks=parse_blocks("00:00-00:00:valle", default_period=TariffPeriod.VALLE),
    )

    # 2026-04-07 01:00 UTC  ==  2026-04-06 22:00 UY (Monday evening, workday)
    now_utc = datetime(2026, 4, 7, 1, 0, tzinfo=_UTC)
    snap = calc.snapshot(now_utc)

    assert snap.current_period == TariffPeriod.VALLE
    # Next change is 2026-04-07 00:00 UY (= midnight end of Monday in UY)
    assert snap.next_change_at == datetime(2026, 4, 7, 0, 0, tzinfo=_UY)
    assert snap.next_period == TariffPeriod.VALLE


def test_utc_datetime_determines_holiday_in_uy_calendar() -> None:
    """23:30 UTC on April 30 is 20:30 UY on April 30 — NOT May 1 yet.

    May 1 is a Uruguayan public holiday.  A triple-tariff calculator
    should use the *workday* schedule for April 30 UY (20:30 is punta),
    and the *holiday* schedule the moment the clock crosses midnight in UY.
    """
    calc = TariffCalculator(
        contract_type=ContractType.TRIPLE,
        price_ranges=_price_ranges(),
        workday_blocks=parse_blocks(
            "00:00-07:00:valle,07:00-17:00:llano,17:00-21:00:punta,21:00-00:00:llano",
            default_period=TariffPeriod.LLANO,
        ),
        holiday_blocks=parse_blocks("00:00-00:00:valle", default_period=TariffPeriod.VALLE),
    )

    # 2026-04-30 23:30 UTC  ==  2026-04-30 20:30 UY (still April 30, workday punta)
    now_utc = datetime(2026, 4, 30, 23, 30, tzinfo=_UTC)
    snap = calc.snapshot(now_utc)
    assert snap.current_period == TariffPeriod.PUNTA

    # 2026-05-01 03:00 UTC  ==  2026-05-01 00:00 UY (May 1, national holiday → valle)
    now_utc_holiday = datetime(2026, 5, 1, 3, 0, tzinfo=_UTC)
    snap_holiday = calc.snapshot(now_utc_holiday)
    assert snap_holiday.current_period == TariffPeriod.VALLE
