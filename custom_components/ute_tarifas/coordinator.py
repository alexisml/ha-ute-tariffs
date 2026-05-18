"""Coordinator for UTE tariff sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import ContractType, TariffPeriod
from .tariff import PriceRange, TariffCalculator, TariffSnapshot, parse_blocks

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoordinatorPayload:
    """Coordinator payload."""

    snapshot: TariffSnapshot
    contract_type: ContractType


def _price_ranges_from_config(raw_ranges: list[dict]) -> list[PriceRange]:
    return [
        PriceRange(
            start=date.fromisoformat(entry["start"]),
            end=date.fromisoformat(entry["end"]),
            simple=float(entry["simple"]),
            double_valle=float(entry["double_valle"]),
            double_punta=float(entry["double_punta"]),
            triple_valle=float(entry["triple_valle"]),
            triple_llano=float(entry["triple_llano"]),
            triple_punta=float(entry["triple_punta"]),
        )
        for entry in raw_ranges
    ]


class UteTarifasCoordinator(DataUpdateCoordinator[CoordinatorPayload]):
    """UTE tariff coordinator."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        contract_type = ContractType(config["contract_type"])
        self._calculator = TariffCalculator(
            contract_type=contract_type,
            price_ranges=_price_ranges_from_config(config["price_ranges"]),
            workday_blocks=parse_blocks(
                config.get("schedule_workday", ""),
                default_period=self._default_period(contract_type),
            ),
            weekend_blocks=parse_blocks(
                config.get("schedule_weekend", ""),
                default_period=self._default_period(contract_type),
            ),
            holiday_blocks=parse_blocks(
                config.get("schedule_holiday", ""),
                default_period=self._default_period(contract_type),
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

    @staticmethod
    def _default_period(contract_type: ContractType) -> TariffPeriod:
        if contract_type == ContractType.SIMPLE:
            return TariffPeriod.SIMPLE
        if contract_type == ContractType.TRIPLE:
            return TariffPeriod.LLANO
        return TariffPeriod.VALLE

    async def _async_update_data(self) -> CoordinatorPayload:
        snapshot = self._calculator.snapshot(dt_util.now())
        return CoordinatorPayload(snapshot=snapshot, contract_type=self._contract_type)
