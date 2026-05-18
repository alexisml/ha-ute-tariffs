"""Config flow for UTE Tarifas."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_CONTRACT_TYPE,
    CONF_COUNTRY,
    CONF_PRICE_RANGES,
    CONF_SCHEDULE_HOLIDAY,
    CONF_SCHEDULE_WEEKEND,
    CONF_SCHEDULE_WORKDAY,
    CONF_USE_NATIONAL_HOLIDAYS,
    DEFAULT_COUNTRY,
    DEFAULT_USE_NATIONAL_HOLIDAYS,
    DOMAIN,
    ContractType,
)

DEFAULT_PRICE_RANGE = [
    {
        "start": "2026-01-01",
        "end": "2099-12-31",
        "simple": 8.5,
        "double_valle": 6.0,
        "double_punta": 12.0,
        "triple_valle": 4.5,
        "triple_llano": 8.0,
        "triple_punta": 13.0,
    }
]


class UteTarifasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UTE Tarifas."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle user setup."""
        if user_input is not None:
            return self.async_create_entry(
                title="UTE Tarifas (Residential)",
                data={
                    CONF_CONTRACT_TYPE: user_input[CONF_CONTRACT_TYPE],
                    CONF_PRICE_RANGES: DEFAULT_PRICE_RANGE,
                    CONF_SCHEDULE_WORKDAY: user_input.get(CONF_SCHEDULE_WORKDAY, ""),
                    CONF_SCHEDULE_WEEKEND: user_input.get(CONF_SCHEDULE_WEEKEND, ""),
                    CONF_SCHEDULE_HOLIDAY: user_input.get(CONF_SCHEDULE_HOLIDAY, ""),
                    CONF_COUNTRY: user_input[CONF_COUNTRY],
                    CONF_USE_NATIONAL_HOLIDAYS: user_input[CONF_USE_NATIONAL_HOLIDAYS],
                },
            )

        return self.async_show_form(
            step_id="user",
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
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return UteTarifasOptionsFlow(config_entry)


class UteTarifasOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data
        options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCHEDULE_WORKDAY,
                        default=options.get(
                            CONF_SCHEDULE_WORKDAY,
                            data.get(CONF_SCHEDULE_WORKDAY, ""),
                        ),
                    ): str,
                    vol.Required(
                        CONF_SCHEDULE_WEEKEND,
                        default=options.get(
                            CONF_SCHEDULE_WEEKEND,
                            data.get(CONF_SCHEDULE_WEEKEND, ""),
                        ),
                    ): str,
                    vol.Required(
                        CONF_SCHEDULE_HOLIDAY,
                        default=options.get(
                            CONF_SCHEDULE_HOLIDAY,
                            data.get(CONF_SCHEDULE_HOLIDAY, ""),
                        ),
                    ): str,
                }
            ),
        )
