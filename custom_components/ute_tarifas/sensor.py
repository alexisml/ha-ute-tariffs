"""Sensor platform for UTE tariffs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CoordinatorPayload, UteTarifasCoordinator


@dataclass(frozen=True, kw_only=True)
class UteTarifasSensorDescription(SensorEntityDescription):
    """Sensor description for UTE Tarifas sensors."""

    value_fn: Callable[[CoordinatorPayload], object]


SENSOR_TYPES: list[UteTarifasSensorDescription] = [
    UteTarifasSensorDescription(
        key="current_cost",
        translation_key="current_cost",
        native_unit_of_measurement=f"UYU/{UnitOfEnergy.KILO_WATT_HOUR}",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda payload: payload.snapshot.current_cost,
    ),
    UteTarifasSensorDescription(
        key="current_period",
        translation_key="current_period",
        value_fn=lambda payload: payload.snapshot.current_period,
    ),
    UteTarifasSensorDescription(
        key="next_change",
        translation_key="next_change",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda payload: payload.snapshot.next_change_at,
    ),
    UteTarifasSensorDescription(
        key="next_period",
        translation_key="next_period",
        value_fn=lambda payload: payload.snapshot.next_period,
    ),
    UteTarifasSensorDescription(
        key="contract_type",
        translation_key="contract_type",
        value_fn=lambda payload: payload.contract_type,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UTE Tarifas sensors from a config entry."""
    coordinator: UteTarifasCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        UteTarifasSensor(coordinator, entry, description) for description in SENSOR_TYPES
    )


class UteTarifasSensor(CoordinatorEntity[UteTarifasCoordinator], SensorEntity):
    """A coordinator-backed UTE tariff sensor.

    All five sensors belong to a single "UTE Tarifas" device so they are
    grouped together in the Home Assistant UI rather than appearing as
    orphaned entities.
    """

    _attr_has_entity_name = True
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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="UTE Tarifas",
            manufacturer="UTE",
            model="Residential Tariff",
        )

    @property
    def native_value(self) -> object:
        """Return the current sensor value."""
        payload: CoordinatorPayload = self.coordinator.data
        return self.entity_description.value_fn(payload)
