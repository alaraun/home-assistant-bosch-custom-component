"""Bosch gateway entry config class."""
from __future__ import annotations

import asyncio
import logging
import random
import ssl
from datetime import timedelta
from typing import Any, TYPE_CHECKING

from bosch_thermostat_client.const import HTTP, RECORDING
from bosch_thermostat_client.exceptions import (
    DeviceException,
    EncryptionException,
    FirmwareException,
    UnknownDevice,
)
from homeassistant.components.persistent_notification import (
    async_create as async_create_persistent_notification,
)
from homeassistant.const import CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.json import save_json
from homeassistant.helpers.network import get_url
from homeassistant.util import dt as dt_util
from homeassistant.util.json import load_json

from .const import (
    DOMAIN,
    GATEWAY,
    NOTIFICATION_ID,
    SUPPORTED_PLATFORMS,
)
from .services import async_register_debug_service
from .types import BoschGateway

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from .coordinator import BoschDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

CUSTOM_DB = "custom_bosch_db.json"


def create_notification_firmware(hass: HomeAssistant, msg: str | Exception) -> None:
    """Create notification about firmware to the user."""
    async_create_persistent_notification(
        hass,
        title="Bosch info",
        message=(
            "There are problems with config of your thermostat.\n"
            f"{msg}.\n"
            "You can create issue on Github, but first\n"
            "Go to [Developer Tools/Service](/developer-tools/service) and create bosch.debug_scan.\n"
            "[BoschGithub](https://github.com/bosch-thermostat/home-assistant-bosch-custom-component)"
        ),
        notification_id=NOTIFICATION_ID,
    )


class BoschGatewayEntry:
    """Bosch gateway entry config class."""

    def __init__(
        self,
        hass: HomeAssistant,
        uuid: str,
        host: str,
        protocol: str,
        device_type: str,
        access_key: str,
        access_token: str,
        entry: ConfigEntry,
        password: str | None = None,
    ) -> None:
        """Init Bosch gateway entry config class."""
        self.hass = hass
        self.uuid = uuid
        self._host = host
        self._access_key = access_key
        self._access_token = access_token
        self._device_type = device_type
        self._protocol = protocol
        self._password = password
        self.config_entry = entry
        self._debug_service_registered = False
        self.gateway: BoschGateway | None = None
        self.supported_platforms: list[str] = []
        self._update_lock: asyncio.Lock | None = None
        self.coordinator: BoschDataUpdateCoordinator | None = None

    @property
    def device_id(self) -> str:
        return self.config_entry.entry_id

    async def async_init(self) -> bool:
        """Init async items in entry."""
        import bosch_thermostat_client as bosch

        _LOGGER.debug("Initializing Bosch integration.")
        self._update_lock = asyncio.Lock()

        BoschGatewayClass = bosch.gateway_chooser(device_type=self._device_type)
        verify_ssl = self.config_entry.data.get(CONF_VERIFY_SSL, True)

        from bosch_thermostat_client.const.easycontrol import EASYCONTROL
        from bosch_thermostat_client.const import XMPP

        ssl_context = None
        if self._protocol == HTTP:
            def create_ssl_context():
                import certifi
                context = ssl.create_default_context(cafile=certifi.where())
                if not verify_ssl:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                return context

            ssl_context = await self.hass.async_add_executor_job(create_ssl_context)
        elif self._protocol == XMPP and self._device_type == EASYCONTROL:
            def create_xmpp_ssl_context():
                from bosch_thermostat_client.connectors.easycontrol import _CA_CERT_PATH
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.load_verify_locations(cafile=str(_CA_CERT_PATH))
                return context

            ssl_context = await self.hass.async_add_executor_job(create_xmpp_ssl_context)


        session = (
            async_get_clientsession(self.hass, verify_ssl=verify_ssl)
            if self._protocol == HTTP
            else None
        )
        self.gateway = BoschGatewayClass(
            session=session,
            session_type=self._protocol,
            host=self._host,
            access_key=self._access_key,
            access_token=self._access_token,
            password=self._password,
            ssl_context=ssl_context,
        )

        # Manually trigger async context manager entry
        await self.gateway.__aenter__()

        if await self.async_init_bosch():
            from .coordinator import BoschDataUpdateCoordinator
            from .helpers import async_setup_platforms

            self.coordinator = BoschDataUpdateCoordinator(
                self.hass, self.gateway, self.uuid, self.supported_platforms, self.config_entry
            )
            
            await self.coordinator.async_config_entry_first_refresh()

            device_registry = dr.async_get(self.hass)
            device_registry.async_get_or_create(
                config_entry_id=self.config_entry.entry_id,
                identifiers={(DOMAIN, self.uuid)},
                manufacturer=self.gateway.device_model,
                model=self.gateway.device_type,
                name=self.gateway.device_name,
                sw_version=self.gateway.firmware,
            )

            await async_setup_platforms(self, self.config_entry)
            if GATEWAY in self.hass.data[DOMAIN][self.uuid]:
                _LOGGER.debug("Registering debug services.")
                async_register_debug_service(hass=self.hass, entry=self)

            # Recording sensors still use their own scheduling for now
            self.hass.loop.create_task(self.coordinator.async_recording_sensors_update())

            _LOGGER.debug(
                "Bosch component registered with platforms %s.",
                self.supported_platforms,
            )
            return True
        return False

    async def async_init_bosch(self) -> bool:
        """Initialize Bosch gateway module."""
        _LOGGER.debug("Checking connection to Bosch gateway as %s.", self._host)
        assert self.gateway
        try:
            await self.gateway.check_connection()
        except (FirmwareException) as err:
            create_notification_firmware(hass=self.hass, msg=err)
            _LOGGER.error(err)
            return False
        except (UnknownDevice, EncryptionException) as err:
            _LOGGER.error(
                "Cannot connect to Bosch gateway (%s): %s. Please verify your password and access key.",
                self.uuid,
                err,
            )
            raise ConfigEntryNotReady(
                f"Cannot connect to Bosch gateway, host {self._host} with UUID: {self.uuid}"
            )
        if not self.gateway.uuid:
            raise ConfigEntryNotReady(
                f"Cannot connect to Bosch gateway, host {self._host} with UUID: {self.uuid}"
            )
        _LOGGER.debug("Bosch BUS detected: %s", self.gateway.bus_type)
        if not self.gateway.database:
            custom_db = load_json(self.hass.config.path(CUSTOM_DB), default=None)
            if custom_db:
                _LOGGER.debug("Loading custom db file.")
                assert isinstance(custom_db, dict)
                await self.gateway.custom_initialize(custom_db)
        if self.gateway.database:
            supported_bosch = await self.gateway.get_capabilities()
            _LOGGER.debug("Bosch supported capabilities: %s", supported_bosch)
            for supported in supported_bosch:
                elements = SUPPORTED_PLATFORMS.get(supported, [])
                for element in elements:
                    if element not in self.supported_platforms:
                        self.supported_platforms.append(element)
        self.hass.data[DOMAIN][self.uuid][GATEWAY] = self.gateway
        _LOGGER.debug("Bosch initialized.")
        return True

    async def custom_put(self, path: str, value: Any) -> None:
        """Send PUT directly to gateway without parsing."""
        assert self.gateway
        await self.gateway.raw_put(path=path, value=value)

    async def custom_get(self, path: str) -> Any:
        """Fetch value from gateway."""
        assert self._update_lock
        assert self.gateway
        async with self._update_lock:
            return await self.gateway.raw_query(path=path)

    async def make_rawscan(self, filename: str) -> dict:
        """Create rawscan from service."""
        rawscan = {}
        assert self._update_lock
        assert self.gateway
        async with self._update_lock:
            _LOGGER.debug("Starting rawscan of Bosch component")
            async_create_persistent_notification(
                self.hass,
                title="Bosch scan",
                message=("Starting rawscan"),
                notification_id=NOTIFICATION_ID,
            )
            rawscan = await self.gateway.rawscan()
            try:
                save_json(filename, rawscan)
            except (FileNotFoundError, OSError) as err:
                _LOGGER.error("Can't create file. %s", err)
                if rawscan:
                    return rawscan
            url = "{}{}{}".format(
                get_url(self.hass),
                "/local/bosch_scan.json?v",
                random.randint(0, 5000),
            )
            _LOGGER.debug("Rawscan success. Your URL: %s", url)
            async_create_persistent_notification(
                self.hass,
                title="Bosch scan",
                message=f"[{url}]({url})",
                notification_id=NOTIFICATION_ID,
            )
        return rawscan

    async def async_reset(self) -> bool:
        """Reset this device to default state."""
        _LOGGER.debug("Unloading Bosch module for UUID: %s", self.uuid)
        if self.gateway:
            await self.gateway.__aexit__(None, None, None)
        
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(
                    self.hass.config_entries.async_forward_entry_unload(
                        self.config_entry, platform
                    )
                )
                for platform in self.supported_platforms
            ]
        return all(task.result() for task in tasks)
