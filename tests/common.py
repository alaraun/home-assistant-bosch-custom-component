"""Common utilities for Bosch integration tests."""
import json
import os
from unittest.mock import AsyncMock, MagicMock

FIXTURE_PATH = ".planning/phases/05-testing-foundation/fixtures"

def load_fixture(device_type, filename="rawscan.json"):
    """Load a fixture for a specific device type."""
    path = os.path.join(FIXTURE_PATH, device_type, filename)
    with open(path, "r") as f:
        return json.load(f)

class MockEntity:
    """Mock Bosch entity."""
    def __init__(self, id, name, value, unit=None, kind="regular"):
        self.id = id
        self.attr_id = id
        self.name = name
        self.value = value
        self.unit_of_measure = unit
        self.kind = kind
        self.update = AsyncMock()
        self.parent_id = None
        self.state = value
        self.device_class = None
        self.state_class = None
        self.device_name = name
        self.entity_category = None
        self.icon = None
        self.path = id
        self.update_initialized = True

    def get_property(self, property_name):
        """Mock get property."""
        if property_name == self.id:
            return {"value": self.value, "unitOfMeasure": self.unit_of_measure}
        return {}

class MockClimate:
    """Mock Bosch climate circuit."""
    def __init__(self, id, name):
        self.id = id
        self.attr_id = id
        self.name = name
        self.parent_id = None
        self.current_temp = 21.0
        self.target_temperature = 20.0
        self.ha_mode = "heat"
        self.ha_modes = ["heat", "off"]
        self.hvac_action = "heat"
        self.temp_units = "C"
        self.setpoint = 20.0
        self.schedule = None
        self.state = "heat"
        self.extra_state_attributes = {}
        self.support_presets = False
        self.preset_modes = []
        self.update = AsyncMock()
        self.set_ha_mode = AsyncMock(return_value=1)
        self.set_temperature = AsyncMock()
        self.max_temp = 30.0
        self.min_temp = 5.0

class MockGateway:
    """Mock Bosch Gateway."""

    def __init__(self, **kwargs):
        """Initialize mock gateway."""
        self.session_type = kwargs.get("session_type")
        self.host = kwargs.get("host")
        self.access_key = kwargs.get("access_key", "abc")
        self.access_token = kwargs.get("access_token")
        self.password = kwargs.get("password")
        self.uuid = "123456789"
        self.device_model = "EasyControl"
        self.device_type = "EASYCONTROL"
        self.firmware = "04.06.07"
        self.device_name = "Bosch Gateway"
        self.bus_type = "EMS"
        self.database = {"sensors": []}
        
        # Internal state
        self._capabilities = ["sensor", "hc"]
        self.sensors = []
        self.binary_sensors = []
        self.heating_circuits = []
        self.dhw_circuits = []
        self.switches = []
        self.numbers = []
        self._circuits = {}
        
        self.check_connection = AsyncMock(return_value=self.uuid)
        self.rawscan = AsyncMock(return_value={})
        self.get_capabilities = AsyncMock(side_effect=self._async_get_capabilities)
        self.custom_initialize = AsyncMock()
        self.raw_put = AsyncMock()
        self.raw_query = AsyncMock()
        self.initialize_sensors = AsyncMock()
        self.initialize_switches = AsyncMock()
        
    async def _async_get_capabilities(self):
        """Mock get capabilities."""
        return self._capabilities

    def get_circuits(self, circ_type):
        """Mock get circuits."""
        return self._circuits.get(circ_type, [])

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

    async def close(self):
        """Close connection."""
        pass
