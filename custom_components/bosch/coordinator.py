"""DataUpdateCoordinator for Bosch integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from bosch_thermostat_client.const import RECORDING, XMPP
from bosch_thermostat_client.exceptions import DeviceException
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    BINARY_SENSOR,
    CLIMATE,
    CONF_PROTOCOL,
    DOMAIN,
    NUMBER,
    PLATFORM_TO_BOSCH_MAP,
    SENSOR,
    SWITCH,
    WATER_HEATER,
)
from .types import BoschGateway, BoschObject

_LOGGER = logging.getLogger(__name__)

class BoschDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Bosch data."""

    def __init__(
        self,
        hass: HomeAssistant,
        gateway: BoschGateway,
        uuid: str,
        supported_platforms: list[str],
        entry: Any,
    ) -> None:
        """Initialize the coordinator."""
        self.gateway = gateway
        self.uuid = uuid
        self.supported_platforms = supported_platforms
        self.entry = entry
        
        # Get options with defaults
        protocol = entry.data.get(CONF_PROTOCOL)
        default_concurrency = 1 if protocol == XMPP else 3
        concurrency = entry.options.get("concurrency", default_concurrency)
        scan_interval = entry.options.get("scan_interval", 60)
        
        self._semaphore = asyncio.Semaphore(concurrency)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"Bosch {uuid}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch data from Bosch."""
        _LOGGER.debug("Updating Bosch thermostat entities via coordinator.")
        
        tasks = []
        for platform in self.supported_platforms:
            if bosch_attr := PLATFORM_TO_BOSCH_MAP.get(platform):
                bosch_objects = getattr(self.gateway, bosch_attr, [])
                for obj in bosch_objects:
                    tasks.append(self._async_update_object(obj))
        
        if tasks:
            async with asyncio.TaskGroup() as tg:
                for task in tasks:
                    tg.create_task(task)
        
        _LOGGER.debug("Bosch update completed successfully")
        return True

    async def _async_update_object(self, obj: BoschObject) -> None:
        """Update a single Bosch object with concurrency control."""
        async with self._semaphore:
            try:
                _LOGGER.debug("Updating Bosch object: %s", obj.name)
                await obj.update()
            except DeviceException as err:
                _LOGGER.debug("Error updating %s: %s", obj.name, err)
            except Exception as err:
                _LOGGER.warning("Unexpected error updating %s: %s", obj.name, err)

    async def async_recording_sensors_update(self, now: datetime | None = None) -> None:
        """Update of 1-hour sensors.

        It suppose to be called only once an hour
        so sensor get's average data from Bosch.
        """
        entities = self.hass.data[DOMAIN][self.uuid].get(RECORDING, [])
        if not entities:
            return
        recording_callback = self.hass.data[DOMAIN][self.uuid].pop(
            "recording_interval", None
        )
        if recording_callback is not None:
            recording_callback()
            recording_callback = None
        updated = False
        now = dt_util.now()
        tasks = []
        for entity in entities:
            if entity.enabled:
                _LOGGER.debug("Updating component 1-hour Sensor by %s", id(self))
                tasks.append(self._async_update_object(entity.bosch_object))
        
        if tasks:
            async with asyncio.TaskGroup() as tg:
                for task in tasks:
                    tg.create_task(task)
            updated = True

        def rounder(t):
            matching_seconds = [0]
            matching_minutes = [6]  # 6
            matching_hours = dt_util.parse_time_expression("*", 0, 23)
            return dt_util.find_next_time_expression_time(
                t, matching_seconds, matching_minutes, matching_hours
            )

        nexti = rounder(now + timedelta(seconds=1))
        self.hass.data[DOMAIN][self.uuid][
            "recording_interval"
        ] = async_track_point_in_utc_time(
            self.hass, self.async_recording_sensors_update, nexti
        )
        _LOGGER.debug("Next update of 1-hour sensors scheduled at: %s", nexti)
        if updated:
            _LOGGER.debug("Bosch 1-hour entitites updated.")
