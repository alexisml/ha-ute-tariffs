"""Constants for the UTE Tarifas integration."""

from __future__ import annotations

from enum import StrEnum

DOMAIN = "ute_tarifas"

CONF_CONTRACT_TYPE = "contract_type"
CONF_PRICE_RANGES = "price_ranges"
CONF_SCHEDULE_WORKDAY = "schedule_workday"
CONF_SCHEDULE_WEEKEND = "schedule_weekend"
CONF_SCHEDULE_HOLIDAY = "schedule_holiday"
CONF_COUNTRY = "country"
CONF_USE_NATIONAL_HOLIDAYS = "use_national_holidays"

DEFAULT_COUNTRY = "UY"
DEFAULT_USE_NATIONAL_HOLIDAYS = True


class ContractType(StrEnum):
    """Residential contract type supported by UTE."""

    SIMPLE = "simple"
    DOUBLE = "double"
    TRIPLE = "triple"


class TariffPeriod(StrEnum):
    """Tariff period names."""

    SIMPLE = "simple"
    VALLE = "valle"
    LLANO = "llano"
    PUNTA = "punta"
