"""Constants for the UTE Tarifas integration."""

from __future__ import annotations

from enum import StrEnum

DOMAIN = "ute_tarifas"

CONF_CONTRACT_TYPE = "contract_type"
CONF_SCHEDULE_WORKDAY = "schedule_workday"
CONF_SCHEDULE_WEEKEND = "schedule_weekend"
CONF_SCHEDULE_HOLIDAY = "schedule_holiday"
CONF_COUNTRY = "country"
CONF_USE_NATIONAL_HOLIDAYS = "use_national_holidays"
CONF_MONTHLY_KWH_ENTITY = "monthly_kwh_entity"

DEFAULT_COUNTRY = "UY"
DEFAULT_USE_NATIONAL_HOLIDAYS = True

# IVA (Impuesto al Valor Agregado) rate applied to UTE tariffs in Uruguay.
IVA_RATE = 0.22

# Maximum number of (country, year) entries kept in the holiday cache.
# In practice only 1-2 years are ever needed per HA instance lifetime.
HOLIDAY_CACHE_MAX_SIZE = 5

# Maximum number of day-boundaries to scan forward when looking for the next
# tariff period change (e.g. skipping same-period weekend days).
SCHEDULE_SCAN_DAYS = 14


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
