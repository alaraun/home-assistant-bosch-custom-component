"""Bosch base entity."""
from __future__ import annotations
from typing import Any, TYPE_CHECKING

from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DEFAULT_MAX_TEMP, DEFAULT_MIN_TEMP, DOMAIN
from homeassistant.helpers.entity import DeviceInfo
from .types import BoschGateway, BoschObject

if TYPE_CHECKING:
    from .coordinator import BoschDataUpdateCoordinator
    from homeassistant.core import HomeAssistant

class BoschEntity(CoordinatorEntity):
    """Bosch base entity class."""
    coordinator: BoschDataUpdateCoordinator

    def __init__(
        self, 
        coordinator: BoschDataUpdateCoordinator, 
        bosch_object: BoschObject,
        gateway: BoschGateway,
        uuid: str,
        domain_name: str | None = None
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._bosch_object = bosch_object
        self._gateway = gateway
        self._uuid = uuid
        self._domain_name = domain_name or getattr(self, "_domain_name", None)
        self._name = bosch_object.name
        self._name_prefix = ""
        self.hass: HomeAssistant = coordinator.hass

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def device_name(self) -> str:
        """Return name displayed in device_info."""
        return f"{self._name_prefix} {self._name}"

    @property
    def bosch_object(self) -> BoschObject:
        """Return upstream component. Used for refreshing."""
        return self._bosch_object

    @property
    def _domain_identifier(self) -> set[tuple[str, str]]:
        if self._bosch_object.parent_id:
            return {(DOMAIN, f"{self._uuid}_{self._bosch_object.parent_id}")}
        return {(DOMAIN, f"{self._uuid}_{self._domain_name or ''}")}

    @property
    def device_info(self) -> DeviceInfo:
        """Get attributes about the device."""
        device_info = DeviceInfo(
            identifiers=self._domain_identifier,
            manufacturer=self._gateway.device_model,
            model=self._gateway.device_type,
            name=self.device_name,
            sw_version=self._gateway.firmware,
            hw_version=self._uuid,
        )
        if self._domain_identifier != {(DOMAIN, self._uuid)}:
            device_info["via_device"] = (DOMAIN, self._uuid)
        return device_info


class BoschClimateWaterEntity(BoschEntity):
    """Bosch climate and water entities base class."""

    def __init__(
        self, 
        coordinator: BoschDataUpdateCoordinator, 
        bosch_object: BoschObject,
        gateway: BoschGateway,
        uuid: str,
    ) -> None:
        """Initialize the climate/water entity."""
        super().__init__(coordinator, bosch_object, gateway, uuid)
        self._temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_unique_id = f"{self._uuid}{self._bosch_object.id}"
        self._current_temperature: float | None = None
        self._state: Any = None
        self._target_temperature: float | None = None

    @property
    def _domain_identifier(self) -> set[tuple[str, str]]:
        return {(DOMAIN, f"{self._uuid}_{self._bosch_object.id}")}

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return self._temperature_unit

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return (
            self._bosch_object.min_temp
            if self._bosch_object.min_temp
            else DEFAULT_MIN_TEMP
        )

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return (
            self._bosch_object.max_temp
            if self._bosch_object.max_temp
            else DEFAULT_MAX_TEMP
        )
