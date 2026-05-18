"""Sensor platform for UTE tariffs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CoordinatorPayload, UteTarifasCoordinator


@dataclass(frozen=True, kw_only=True)
class UteTarifasSensorDescription(SensorEntityDescription):
    """Sensor description for the integration."""

    value_fn: Callable[[CoordinatorPayload], object]


SENSOR_TYPES = [
    UteTarifasSensorDescription(
        key="current_cost",
        name="UTE Current Cost",
        native_unit_of_measurement=f"UYU/{UnitOfEnergy.KILO_WATT_HOUR}",
        value_fn=lambda payload: payload.snapshot.current_cost,
    ),
    UteTarifasSensorDescription(
        key="current_period",
        name="UTE Current Period",
        value_fn=lambda payload: payload.snapshot.current_period,
    ),
    UteTarifasSensorDescription(
        key="next_change",
        name="UTE Next Cost Change",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda payload: payload.snapshot.next_change_at,
    ),
    UteTarifasSensorDescription(
        key="next_period",
        name="UTE Next Period",
        value_fn=lambda payload: payload.snapshot.next_period,
    ),
    UteTarifasSensorDescription(
        key="contract_type",
        name="UTE Residential Contract",
        value_fn=lambda payload: payload.contract_type,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UTE sensors from a config entry."""
    coordinator: UteTarifasCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        UteTarifasSensor(coordinator, entry, description) for description in SENSOR_TYPES
    )


class UteTarifasSensor(CoordinatorEntity[UteTarifasCoordinator], SensorEntity):
    """A coordinator-backed UTE tariff sensor."""

    entity_description: UteTarifasSensorDescription

    def __init__(
        self,
        coordinator: UteTarifasCoordinator,
        entry: ConfigEntry,
        description: UteTarifasSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        """Return current state."""
        payload: CoordinatorPayload = self.coordinator.data
        return self.entity_description.value_fn(payload)
