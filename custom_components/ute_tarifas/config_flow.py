"""Config flow for UTE Tarifas."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_CONTRACT_TYPE,
    CONF_MONTHLY_KWH_ENTITY,
    CONF_PUNTA_SCHEDULE,
    CONF_USE_NATIONAL_HOLIDAYS,
    DEFAULT_PUNTA_SCHEDULE,
    DEFAULT_USE_NATIONAL_HOLIDAYS,
    DOMAIN,
    PUNTA_SCHEDULE_OPTIONS,
    ContractType,
)


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

        if user_input is not None:
            return self.async_create_entry(
                title="UTE Tarifas",
                data={
                    CONF_CONTRACT_TYPE: user_input[CONF_CONTRACT_TYPE],
                    CONF_PUNTA_SCHEDULE: user_input.get(
                        CONF_PUNTA_SCHEDULE, DEFAULT_PUNTA_SCHEDULE
                    ),
                    CONF_USE_NATIONAL_HOLIDAYS: user_input[CONF_USE_NATIONAL_HOLIDAYS],
                    CONF_MONTHLY_KWH_ENTITY: (
                        user_input.get(CONF_MONTHLY_KWH_ENTITY, "").strip()
                    ),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONTRACT_TYPE, default=ContractType.SIMPLE): vol.In(
                        [ct.value for ct in ContractType]
                    ),
                    vol.Optional(
                        CONF_PUNTA_SCHEDULE, default=DEFAULT_PUNTA_SCHEDULE
                    ): vol.In(PUNTA_SCHEDULE_OPTIONS),
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
    """Allow the user to update the punta window and holiday settings after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show and process the punta-schedule and holiday-settings form."""
        data = self.config_entry.data
        options = self.config_entry.options

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_PUNTA_SCHEDULE: user_input.get(
                        CONF_PUNTA_SCHEDULE, DEFAULT_PUNTA_SCHEDULE
                    ),
                    CONF_MONTHLY_KWH_ENTITY: (
                        user_input.get(CONF_MONTHLY_KWH_ENTITY, "").strip()
                    ),
                    CONF_USE_NATIONAL_HOLIDAYS: user_input[CONF_USE_NATIONAL_HOLIDAYS],
                },
            )

        def _default(key: str, fallback: object = "") -> object:
            return options.get(key, data.get(key, fallback))

        schema = {
            vol.Optional(
                CONF_PUNTA_SCHEDULE,
                default=_default(CONF_PUNTA_SCHEDULE, DEFAULT_PUNTA_SCHEDULE),
            ): vol.In(PUNTA_SCHEDULE_OPTIONS),
            vol.Optional(
                CONF_MONTHLY_KWH_ENTITY,
                default=_default(CONF_MONTHLY_KWH_ENTITY) or "",
            ): str,
            vol.Optional(
                CONF_USE_NATIONAL_HOLIDAYS,
                default=options.get(
                    CONF_USE_NATIONAL_HOLIDAYS,
                    data.get(CONF_USE_NATIONAL_HOLIDAYS, DEFAULT_USE_NATIONAL_HOLIDAYS),
                ),
            ): bool,
        }
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )
