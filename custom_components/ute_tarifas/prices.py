"""Canonical UTE residential tariff data.

This module is the **single source of truth** for UTE prices and time-of-use
schedules.  Both are encoded with effective date ranges so future changes take
effect automatically on the specified date — no HA restart or user action is
required.

Updating prices
---------------
1. Set ``end`` on the current last entry to the day before the new rates apply.
2. Append a new :class:`~custom_components.ute_tarifas.tariff.PriceRange` with
   the new rates and the correct ``start`` / ``end`` dates.

Example::

    # Old entry (close it)
    PriceRange(
        start=date(2026, 1, 1), end=date(2026, 11, 30),
        simple_low=6.744, simple_mid=8.452, simple_high=10.539,
        double_llano=4.771, double_punta=12.034,
        triple_valle=2.443, triple_llano=5.172, triple_punta=12.034,
    ),
    # New entry (append)
    PriceRange(
        start=date(2026, 12, 1), end=date(2099, 12, 31),
        simple_low=7.0, simple_mid=8.8, simple_high=11.0,
        double_llano=5.0, double_punta=12.5,
        triple_valle=2.5, triple_llano=5.4, triple_punta=12.5,
    ),

Updating a schedule (e.g. new punta hours from 2027-01-01)
-----------------------------------------------------------
1. Set ``end=date(2026, 12, 31)`` on the current last entry for that contract.
2. Append a new :class:`~custom_components.ute_tarifas.tariff.ScheduleRange`
   with ``start=date(2027, 1, 1)`` and the revised blocks.

Both types of change propagate to all users on the specified date without
requiring any reconfiguration.

Sources
-------
* https://www.ute.com.uy/Tarifas
"""

from __future__ import annotations

from datetime import date, time

from .const import ContractType, TariffPeriod
from .tariff import PriceRange, ScheduleRange, TimeBlock

# ---------------------------------------------------------------------------
# Reusable block lists
# ---------------------------------------------------------------------------

_SIMPLE_ALL_DAY: list[TimeBlock] = [
    TimeBlock(time(0, 0), time(0, 0), TariffPeriod.SIMPLE),
]

# DOUBLE (Doble Horario) off-peak is LLANO; weekends and holidays are all-llano.
_LLANO_ALL_DAY: list[TimeBlock] = [
    TimeBlock(time(0, 0), time(0, 0), TariffPeriod.LLANO),
]

# TRIPLE (Triple Horario) weekends and holidays have no punta:
# valle (00:00–07:00) and llano (07:00–24:00).
_TRIPLE_WEEKEND_HOLIDAY: list[TimeBlock] = [
    TimeBlock(time(0, 0), time(7, 0), TariffPeriod.VALLE),
    TimeBlock(time(7, 0), time(0, 0), TariffPeriod.LLANO),
]

# Doble Horario workday: llano (00:00–18:00, 22:00–24:00) and punta (18:00–22:00).
_DOUBLE_WORKDAY: list[TimeBlock] = [
    TimeBlock(time(0, 0), time(18, 0), TariffPeriod.LLANO),
    TimeBlock(time(18, 0), time(22, 0), TariffPeriod.PUNTA),
    # end=time(0, 0) is the "until midnight" sentinel; see _contains() in tariff.py
    TimeBlock(time(22, 0), time(0, 0), TariffPeriod.LLANO),
]

_TRIPLE_WORKDAY: list[TimeBlock] = [
    TimeBlock(time(0, 0), time(7, 0), TariffPeriod.VALLE),
    TimeBlock(time(7, 0), time(18, 0), TariffPeriod.LLANO),
    TimeBlock(time(18, 0), time(22, 0), TariffPeriod.PUNTA),
    # end=time(0, 0) is the "until midnight" sentinel; see _contains() in tariff.py
    TimeBlock(time(22, 0), time(0, 0), TariffPeriod.LLANO),
]

# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------
# Each entry covers [start, end] inclusive (both bounds are part of the range).
# Keep past entries so that historical date queries remain meaningful.
#
# All prices are in UYU/kWh **excluding IVA** (22 %).
# Source: https://www.ute.com.uy/Tarifas
#
# Simple contract has three consumption tiers (monthly kWh thresholds):
#   simple_low  — first 100 kWh/month
#   simple_mid  — 101–600 kWh/month
#   simple_high — 601+ kWh/month

UTE_PRICE_RANGES: list[PriceRange] = [
    # Valid from 2026-01-01 — update end date when a new entry is added
    PriceRange(
        start=date(2026, 1, 1),
        end=date(2099, 12, 31),
        simple_low=6.744,
        simple_mid=8.452,
        simple_high=10.539,
        double_llano=4.771,
        double_punta=12.034,
        triple_valle=2.443,
        triple_llano=5.172,
        triple_punta=12.034,
    ),
]

# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------
# One list of ScheduleRange per contract type.  Multiple entries allow
# encoding future schedule changes with their effective start date.

UTE_SCHEDULE_RANGES: dict[ContractType, list[ScheduleRange]] = {
    ContractType.SIMPLE: [
        ScheduleRange(
            start=date(2000, 1, 1),
            end=date(2099, 12, 31),
            workday_blocks=_SIMPLE_ALL_DAY,
            weekend_blocks=_SIMPLE_ALL_DAY,
            holiday_blocks=_SIMPLE_ALL_DAY,
        ),
    ],
    ContractType.DOUBLE: [
        ScheduleRange(
            start=date(2000, 1, 1),
            end=date(2099, 12, 31),
            workday_blocks=_DOUBLE_WORKDAY,
            weekend_blocks=_LLANO_ALL_DAY,
            holiday_blocks=_LLANO_ALL_DAY,
        ),
    ],
    ContractType.TRIPLE: [
        ScheduleRange(
            start=date(2000, 1, 1),
            end=date(2099, 12, 31),
            workday_blocks=_TRIPLE_WORKDAY,
            weekend_blocks=_TRIPLE_WEEKEND_HOLIDAY,
            holiday_blocks=_TRIPLE_WEEKEND_HOLIDAY,
        ),
    ],
}
