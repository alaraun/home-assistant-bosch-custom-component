"""Base sensor component."""
from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ..coordinator import BoschDataUpdateCoordinator

from bosch_thermostat_client.const import UNITS, VALUE
from bosch_thermostat_client.const.ivt import INVALID
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from ..bosch_entity import BoschEntity
from ..const import UNITS_CONVERTER, WORKING_TIME
from ..types import BoschGateway, BoschObject

_LOGGER = logging.getLogger(__name__)

entity_categories = {"diagnostic": EntityCategory.DIAGNOSTIC}


class BoschBaseSensor(BoschEntity, SensorEntity):
    """Base class for all sensor entities."""

    def __init__(
        self,
        coordinator: BoschDataUpdateCoordinator,
        uuid: str,
        bosch_object: BoschObject,
        gateway: BoschGateway,
        name: str,
        attr_uri: str,
        domain_name: str | None = None,
        circuit_type: str | None = None,
        is_enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator=coordinator,
            uuid=uuid,
            bosch_object=bosch_object,
            gateway=gateway,
            domain_name=domain_name,
        )
        if not circuit_type:
            self._name = (
                f"{domain_name} {name}"
                if domain_name != "Sensors" and domain_name
                else name
            )
        else:
            self._name = f"{self._bosch_object.parent_id} {name}"
        self._attr_uri = attr_uri
        self._attr_device_class = cast(
            SensorDeviceClass, self._bosch_object.device_class
        )
        if self._bosch_object.attr_id == WORKING_TIME:
            self._attr_device_class = SensorDeviceClass.DURATION

        self._attr_state_class = cast(
            SensorStateClass, self._bosch_object.state_class
        )
        self._attr_entity_category = entity_categories.get(
            self._bosch_object.entity_category or "", None
        )
        self._update_init = True
        if not hasattr(self, "_attr_unique_id") or not self._attr_unique_id:
            self._attr_unique_id = (
                f"{self._domain_name}{self._bosch_object.parent_id}{self._bosch_object.id}{self._uuid}"
                if self._bosch_object.parent_id
                else f"{self._domain_name}{self._bosch_object.id}{self._uuid}"
            )

        self._circuit_type = circuit_type
        self._attr_entity_registry_enabled_default = is_enabled

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        data = self._bosch_object.get_property(self._attr_uri)
        if not data or data.get(INVALID, False):
            return None
        state = data.get(VALUE, INVALID)
        if state in (INVALID, "unavailable"):
            if not self._bosch_object.update_initialized:
                return (
                    None
                    if self._attr_state_class
                    and self._attr_state_class == SensorStateClass.MEASUREMENT
                    else self._bosch_object.state
                )
            return None

        # Sanity check for numeric values
        if (
            self._attr_state_class == SensorStateClass.MEASUREMENT
            or self._attr_device_class
            in (
                SensorDeviceClass.TEMPERATURE,
                SensorDeviceClass.ENERGY,
                SensorDeviceClass.POWER,
                SensorDeviceClass.VOLTAGE,
                SensorDeviceClass.CURRENT,
                SensorDeviceClass.GAS,
                SensorDeviceClass.WATER,
            )
        ):
            try:
                if state is not None:
                    float(state)
            except (ValueError, TypeError):
                _LOGGER.error(
                    "Sensor %s has numeric state class/device class but received non-numeric value: %s (type %s). URI: %s",
                    self.entity_id or self._name,
                    state,
                    type(state),
                    self._attr_uri,
                )
                return None

        return state

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the sensor."""
        if self._bosch_object.attr_id == WORKING_TIME:
            return UnitOfTime.MINUTES
        data = self._bosch_object.get_property(self._attr_uri)
        if data and not isinstance(data, list):
            return UNITS_CONVERTER.get(data.get(UNITS, ""))
        return None

    @property
    def suggested_unit_of_measurement(self) -> str | None:
        """Return the suggested unit of measurement."""
        if self._bosch_object.attr_id == WORKING_TIME:
            return UnitOfTime.HOURS
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        data = self._bosch_object.get_property(self._attr_uri)
        if not data:
            return {"stateExtra": self._bosch_object.state_message}
        return {
            **data,
            "stateExtra": self._bosch_object.state,
            "path": self._bosch_object.path,
        }

