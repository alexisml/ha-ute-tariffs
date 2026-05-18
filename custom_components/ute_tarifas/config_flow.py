"""Config flow for UTE Tarifas."""

from __future__ import annotations

from typing import Any

import holidays
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

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
    DOMAIN,
    ContractType,
    TariffPeriod,
)
from .tariff import parse_blocks


def _default_period_for(contract_type: str) -> TariffPeriod:
    """Return the baseline period used when validating a schedule string."""
    ct = ContractType(contract_type)
    if ct == ContractType.SIMPLE:
        return TariffPeriod.SIMPLE
    if ct == ContractType.DOUBLE:
        return TariffPeriod.LLANO
    return TariffPeriod.VALLE


def _validate_schedule(raw: str, default_period: TariffPeriod) -> str | None:
    """Return an error key when *raw* is not a valid schedule string, else ``None``."""
    if not raw.strip():
        return None
    try:
        parse_blocks(raw, default_period=default_period)
    except (ValueError, KeyError):
        return "invalid_schedule"
    return None


def _validate_country(raw: str) -> tuple[str, str | None]:
    """Normalize and validate a country code.

    Returns ``(normalized_code, error_key)`` where *error_key* is ``None`` on
    success or ``"invalid_country"`` when the code is not supported by the
    ``holidays`` package.
    """
    code = raw.strip().upper()
    try:
        holidays.country_holidays(code)
    except (KeyError, NotImplementedError):
        return code, "invalid_country"
    return code, None


class UteTarifasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow for UTE Tarifas.

    Only one instance of the integration may be configured at a time —
    ``async_set_unique_id`` + ``_abort_if_unique_id_configured`` enforce this.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the first (and only) setup step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            dp = _default_period_for(user_input[CONF_CONTRACT_TYPE])
            for field in (CONF_SCHEDULE_WORKDAY, CONF_SCHEDULE_WEEKEND, CONF_SCHEDULE_HOLIDAY):
                err = _validate_schedule(user_input.get(field, ""), dp)
                if err:
                    errors[field] = err

            country, country_err = _validate_country(user_input.get(CONF_COUNTRY, DEFAULT_COUNTRY))
            if country_err:
                errors[CONF_COUNTRY] = country_err

            if not errors:
                return self.async_create_entry(
                    title="UTE Tarifas",
                    data={
                        CONF_CONTRACT_TYPE: user_input[CONF_CONTRACT_TYPE],
                        CONF_SCHEDULE_WORKDAY: user_input.get(CONF_SCHEDULE_WORKDAY, "").strip(),
                        CONF_SCHEDULE_WEEKEND: user_input.get(CONF_SCHEDULE_WEEKEND, "").strip(),
                        CONF_SCHEDULE_HOLIDAY: user_input.get(CONF_SCHEDULE_HOLIDAY, "").strip(),
                        CONF_COUNTRY: country,
                        CONF_USE_NATIONAL_HOLIDAYS: user_input[CONF_USE_NATIONAL_HOLIDAYS],
                        CONF_MONTHLY_KWH_ENTITY: (
                            user_input.get(CONF_MONTHLY_KWH_ENTITY, "").strip()
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONTRACT_TYPE, default=ContractType.SIMPLE): vol.In(
                        [ct.value for ct in ContractType]
                    ),
                    vol.Optional(CONF_SCHEDULE_WORKDAY, default=""): str,
                    vol.Optional(CONF_SCHEDULE_WEEKEND, default=""): str,
                    vol.Optional(CONF_SCHEDULE_HOLIDAY, default=""): str,
                    vol.Optional(CONF_COUNTRY, default=DEFAULT_COUNTRY): str,
                    vol.Optional(
                        CONF_USE_NATIONAL_HOLIDAYS,
                        default=DEFAULT_USE_NATIONAL_HOLIDAYS,
                    ): bool,
                    vol.Optional(CONF_MONTHLY_KWH_ENTITY, default=""): str,
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UteTarifasOptionsFlow:
        """Return the options flow handler."""
        return UteTarifasOptionsFlow(config_entry)


class UteTarifasOptionsFlow(config_entries.OptionsFlow):
    """Allow the user to update schedule overrides after initial setup.

    Clearing a schedule field reverts that day type to the built-in canonical
    UTE schedule defined in ``prices.py``.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show and process the schedule-override form."""
        errors: dict[str, str] = {}
        data = self.config_entry.data
        options = self.config_entry.options
        dp = _default_period_for(data.get(CONF_CONTRACT_TYPE, ContractType.SIMPLE))

        if user_input is not None:
            for field in (CONF_SCHEDULE_WORKDAY, CONF_SCHEDULE_WEEKEND, CONF_SCHEDULE_HOLIDAY):
                err = _validate_schedule(user_input.get(field, ""), dp)
                if err:
                    errors[field] = err

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SCHEDULE_WORKDAY: user_input.get(CONF_SCHEDULE_WORKDAY, "").strip(),
                        CONF_SCHEDULE_WEEKEND: user_input.get(CONF_SCHEDULE_WEEKEND, "").strip(),
                        CONF_SCHEDULE_HOLIDAY: user_input.get(CONF_SCHEDULE_HOLIDAY, "").strip(),
                        CONF_MONTHLY_KWH_ENTITY: (
                            user_input.get(CONF_MONTHLY_KWH_ENTITY, "").strip()
                        ),
                    },
                )

        def _default(key: str) -> object:
            return options.get(key, data.get(key, ""))

        schema = {
            vol.Optional(CONF_SCHEDULE_WORKDAY, default=_default(CONF_SCHEDULE_WORKDAY)): str,
            vol.Optional(CONF_SCHEDULE_WEEKEND, default=_default(CONF_SCHEDULE_WEEKEND)): str,
            vol.Optional(CONF_SCHEDULE_HOLIDAY, default=_default(CONF_SCHEDULE_HOLIDAY)): str,
            vol.Optional(
                CONF_MONTHLY_KWH_ENTITY,
                default=_default(CONF_MONTHLY_KWH_ENTITY) or "",
            ): str,
        }
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(schema),
        )
