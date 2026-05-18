"""Coordinator for UTE tariff sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import ContractType, TariffPeriod
from .prices import UTE_PRICE_RANGES, UTE_SCHEDULE_RANGES
from .tariff import (
    ScheduleRange,
    TariffCalculator,
    TariffSnapshot,
    parse_blocks,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoordinatorPayload:
    """Coordinator payload holding the latest tariff snapshot and contract type."""

    snapshot: TariffSnapshot
    contract_type: ContractType


def _default_period(contract_type: ContractType) -> TariffPeriod:
    """Return the default :class:`TariffPeriod` used as a block fallback.

    When a user supplies a partial custom schedule (e.g. workday only), this
    value fills in the ``default_period`` for any unspecified segment, ensuring
    ``parse_blocks("")`` produces a sensible all-day block instead of an error.
    """
    if contract_type == ContractType.SIMPLE:
        return TariffPeriod.SIMPLE
    if contract_type == ContractType.TRIPLE:
        return TariffPeriod.LLANO
    return TariffPeriod.VALLE


def _build_schedule_ranges(
    contract_type: ContractType,
    custom_workday: str,
    custom_weekend: str,
    custom_holiday: str,
) -> list[ScheduleRange]:
    """Build the :class:`ScheduleRange` list for :class:`TariffCalculator`.

    When all three override strings are blank, returns the canonical
    date-bounded list from ``prices.py`` so that any future schedule changes
    encoded there take effect automatically without user action.

    When at least one override is provided, each canonical :class:`ScheduleRange`
    is preserved with its original date bounds.  Only the day-types that have a
    custom string are replaced; blank day-types keep the canonical blocks from
    that range.  This ensures future schedule updates in ``prices.py`` continue
    to apply even when partial overrides are active.
    """
    canonical_ranges = UTE_SCHEDULE_RANGES[contract_type]

    if not (custom_workday or custom_weekend or custom_holiday):
        return canonical_ranges

    dp = _default_period(contract_type)

    return [
        ScheduleRange(
            start=canonical.start,
            end=canonical.end,
            workday_blocks=(
                parse_blocks(custom_workday, default_period=dp)
                if custom_workday
                else canonical.workday_blocks
            ),
            weekend_blocks=(
                parse_blocks(custom_weekend, default_period=dp)
                if custom_weekend
                else canonical.weekend_blocks
            ),
            holiday_blocks=(
                parse_blocks(custom_holiday, default_period=dp)
                if custom_holiday
                else canonical.holiday_blocks
            ),
        )
        for canonical in canonical_ranges
    ]


class UteTarifasCoordinator(DataUpdateCoordinator[CoordinatorPayload]):
    """UTE tariff coordinator.

    Polls the :class:`TariffCalculator` every minute and exposes the result as
    a :class:`CoordinatorPayload` consumed by all UTE sensor entities.

    Prices and schedules are read from ``prices.py`` (the single source of
    truth).  Custom schedule overrides can be set via the options flow and are
    merged with the canonical data in :func:`_build_schedule_ranges`.
    """

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        contract_type = ContractType(config["contract_type"])
        self._calculator = TariffCalculator(
            contract_type=contract_type,
            price_ranges=UTE_PRICE_RANGES,
            schedule_ranges=_build_schedule_ranges(
                contract_type,
                config.get("schedule_workday", ""),
                config.get("schedule_weekend", ""),
                config.get("schedule_holiday", ""),
            ),
            country=config.get("country", "UY"),
            use_national_holidays=config.get("use_national_holidays", True),
        )
        self._contract_type = contract_type

        super().__init__(
            hass,
            _LOGGER,
            name="UTE Tarifas",
            update_interval=timedelta(minutes=1),
        )

    async def _async_update_data(self) -> CoordinatorPayload:
        """Fetch the latest tariff snapshot.

        Wraps :class:`ValueError` (raised when no price/schedule range covers
        the current date) as :class:`UpdateFailed` so the coordinator retries
        on the next poll instead of crashing the integration.
        """
        try:
            snapshot = self._calculator.snapshot(dt_util.now())
        except ValueError as err:
            raise UpdateFailed(f"Tariff calculation failed: {err}") from err
        return CoordinatorPayload(snapshot=snapshot, contract_type=self._contract_type)
