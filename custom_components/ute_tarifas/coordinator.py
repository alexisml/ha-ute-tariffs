"""Coordinator for UTE tariff sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CONTRACT_TYPE,
    CONF_COUNTRY,
    CONF_MONTHLY_KWH_ENTITY,
    CONF_SCHEDULE_HOLIDAY,
    CONF_SCHEDULE_WEEKEND,
    CONF_SCHEDULE_WORKDAY,
    CONF_USE_NATIONAL_HOLIDAYS,
    DEFAULT_COUNTRY,
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
    parse_blocks,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoordinatorPayload:
    """Coordinator payload holding the latest tariff snapshot and contract type."""

    snapshot: TariffSnapshot
    contract_type: ContractType


def _default_period(contract_type: ContractType) -> TariffPeriod:
    """Return a sensible :class:`TariffPeriod` to pass as ``default_period`` to
    :func:`parse_blocks`.

    Note: :func:`_build_schedule_ranges` only calls :func:`parse_blocks` when the override
    string is non-empty, so ``parse_blocks`` will not use this fallback for the blank-string
    case.  This helper is retained so a sensible per-contract default is available if the
    calling code is ever extended to accept partially-specified strings.
    """
    if contract_type == ContractType.SIMPLE:
        return TariffPeriod.SIMPLE
    if contract_type == ContractType.DOUBLE:
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

    wd = custom_workday.strip()
    we = custom_weekend.strip()
    hd = custom_holiday.strip()

    if not (wd or we or hd):
        return canonical_ranges

    dp = _default_period(contract_type)

    return [
        ScheduleRange(
            start=canonical.start,
            end=canonical.end,
            workday_blocks=(
                parse_blocks(wd, default_period=dp)
                if wd
                else canonical.workday_blocks
            ),
            weekend_blocks=(
                parse_blocks(we, default_period=dp)
                if we
                else canonical.weekend_blocks
            ),
            holiday_blocks=(
                parse_blocks(hd, default_period=dp)
                if hd
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
        contract_type = ContractType(config[CONF_CONTRACT_TYPE])
        self._monthly_kwh_entity: str = config.get(CONF_MONTHLY_KWH_ENTITY, "")
        self._calculator = TariffCalculator(
            contract_type=contract_type,
            price_ranges=UTE_PRICE_RANGES,
            schedule_ranges=_build_schedule_ranges(
                contract_type,
                config.get(CONF_SCHEDULE_WORKDAY, ""),
                config.get(CONF_SCHEDULE_WEEKEND, ""),
                config.get(CONF_SCHEDULE_HOLIDAY, ""),
            ),
            country=config.get(CONF_COUNTRY, DEFAULT_COUNTRY),
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
