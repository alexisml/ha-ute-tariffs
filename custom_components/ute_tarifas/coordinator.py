"""Coordinator for UTE tariff sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import time, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CONTRACT_TYPE,
    CONF_MONTHLY_KWH_ENTITY,
    CONF_PUNTA_SCHEDULE,
    CONF_USE_NATIONAL_HOLIDAYS,
    DEFAULT_COUNTRY,
    DEFAULT_PUNTA_SCHEDULE,
    DEFAULT_USE_NATIONAL_HOLIDAYS,
    IVA_RATE,
    ContractType,
    TariffPeriod,
)
from .prices import UTE_PRICE_RANGES, UTE_SCHEDULE_RANGES
from .tariff import (
    ScheduleRange,
    TariffCalculator,
    TariffSnapshot,
    TimeBlock,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoordinatorPayload:
    """Coordinator payload holding the latest tariff snapshot and contract type."""

    snapshot: TariffSnapshot
    contract_type: ContractType


def _build_schedule_ranges(
    contract_type: ContractType,
    punta_schedule: str,
) -> list[ScheduleRange]:
    """Build the :class:`ScheduleRange` list for :class:`TariffCalculator`.

    Uses the canonical UTE schedules from ``prices.py`` as the base.  When
    *punta_schedule* differs from the canonical 18:00–22:00 window, the
    workday punta block is replaced for Double and Triple contracts.
    Simple contracts are not affected (no punta period).
    """
    canonical_ranges = UTE_SCHEDULE_RANGES[contract_type]

    if contract_type == ContractType.SIMPLE:
        return canonical_ranges

    # Parse punta start hour from "HH-HH" format (e.g. "18-22" → 18).
    try:
        punta_start_hour = int(punta_schedule.split("-")[0])
    except (ValueError, IndexError, AttributeError):
        punta_start_hour = 18  # fall back to canonical

    if punta_start_hour == 18:
        return canonical_ranges

    t_punta_start = time(punta_start_hour, 0)
    # punta options are 17, 18, 19 — adding 4 always yields a valid hour (≤23).
    t_punta_end = time(punta_start_hour + 4, 0)

    if contract_type == ContractType.DOUBLE:
        workday_blocks: list[TimeBlock] = [
            TimeBlock(time(0, 0), t_punta_start, TariffPeriod.LLANO),
            TimeBlock(t_punta_start, t_punta_end, TariffPeriod.PUNTA),
            # end=time(0, 0) is the "until midnight" sentinel; see _contains() in tariff.py
            TimeBlock(t_punta_end, time(0, 0), TariffPeriod.LLANO),
        ]
    else:  # TRIPLE
        workday_blocks = [
            TimeBlock(time(0, 0), time(7, 0), TariffPeriod.VALLE),
            TimeBlock(time(7, 0), t_punta_start, TariffPeriod.LLANO),
            TimeBlock(t_punta_start, t_punta_end, TariffPeriod.PUNTA),
            # end=time(0, 0) is the "until midnight" sentinel; see _contains() in tariff.py
            TimeBlock(t_punta_end, time(0, 0), TariffPeriod.LLANO),
        ]

    return [
        ScheduleRange(
            start=canonical.start,
            end=canonical.end,
            workday_blocks=workday_blocks,
            weekend_blocks=canonical.weekend_blocks,
            holiday_blocks=canonical.holiday_blocks,
        )
        for canonical in canonical_ranges
    ]


class UteTarifasCoordinator(DataUpdateCoordinator[CoordinatorPayload]):
    """UTE tariff coordinator.

    Polls the :class:`TariffCalculator` every minute and exposes the result as
    a :class:`CoordinatorPayload` consumed by all UTE sensor entities.

    Prices and schedules are read from ``prices.py`` (the single source of
    truth).  The punta window can be adjusted via the options flow; all other
    schedule details (weekend/holiday all-llano or all-valle) follow the
    canonical UTE rules.
    """

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        contract_type = ContractType(config[CONF_CONTRACT_TYPE])
        self._monthly_kwh_entity: str = config.get(CONF_MONTHLY_KWH_ENTITY, "")
        self._calculator = TariffCalculator(
            contract_type=contract_type,
            price_ranges=UTE_PRICE_RANGES,
            schedule_ranges=_build_schedule_ranges(
                contract_type,
                config.get(CONF_PUNTA_SCHEDULE, DEFAULT_PUNTA_SCHEDULE),
            ),
            country=DEFAULT_COUNTRY,
            use_national_holidays=config.get(
                CONF_USE_NATIONAL_HOLIDAYS, DEFAULT_USE_NATIONAL_HOLIDAYS
            ),
            monthly_kwh=0,
            iva_rate=IVA_RATE,
        )
        self._contract_type = contract_type
        self._last_bad_monthly_state: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name="UTE Tarifas",
            update_interval=timedelta(minutes=1),
        )

    async def _async_update_data(self) -> CoordinatorPayload:
        """Fetch the latest tariff snapshot.

        When a monthly consumption entity is configured, reads its current state
        to select the correct Simple tariff tier.  Falls back to the cheapest
        tier (0 kWh) when the entity is unavailable or not set.

        Wraps :class:`ValueError` (raised when no price/schedule range covers
        the current date) as :class:`UpdateFailed` so the coordinator retries
        on the next poll instead of crashing the integration.
        """
        if self._monthly_kwh_entity:
            state = self.hass.states.get(self._monthly_kwh_entity)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    self._calculator.monthly_kwh = int(float(state.state))
                except (ValueError, TypeError):
                    if state.state != self._last_bad_monthly_state:
                        _LOGGER.warning(
                            "Could not parse monthly consumption from entity %s (state=%r); "
                            "falling back to cheapest Simple tier (Simple contract only — "
                            "ignored for Double/Triple)",
                            self._monthly_kwh_entity,
                            state.state,
                        )
                        self._last_bad_monthly_state = state.state
                    else:
                        _LOGGER.debug(
                            "Monthly consumption entity %s still non-numeric (state=%r); "
                            "using cheapest Simple tier",
                            self._monthly_kwh_entity,
                            state.state,
                        )
                    self._calculator.monthly_kwh = 0
                else:
                    self._last_bad_monthly_state = None
            else:
                self._calculator.monthly_kwh = 0
        try:
            snapshot = self._calculator.snapshot(dt_util.now())
        except ValueError as err:
            raise UpdateFailed(f"Tariff calculation failed: {err}") from err
        return CoordinatorPayload(snapshot=snapshot, contract_type=self._contract_type)
