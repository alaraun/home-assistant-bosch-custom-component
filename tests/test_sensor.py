"""Test the Bosch sensor platform."""
from unittest.mock import patch, MagicMock
import pytest
from homeassistant.const import (
    CONF_ADDRESS,
)
from bosch_thermostat_client.const import XMPP
from bosch_thermostat_client.const.easycontrol import EASYCONTROL
from custom_components.bosch.const import (
    DOMAIN,
    ACCESS_KEY,
    ACCESS_TOKEN,
    CONF_DEVICE_TYPE,
    CONF_PROTOCOL,
    SENSORS,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.common import MockGateway, MockEntity

@pytest.fixture
def mock_gateway():
    """Mock Bosch Gateway."""
    # We need to return an instance from the mock
    gw = MockGateway()
    gw.sensors = [
        MockEntity(id="/system/sensors/temperatures/outdoor_t1", name="Outdoor t1", value=12.5, unit="C")
    ]
    
    with patch(
        "custom_components.bosch.config_flow.gateway_chooser",
        return_value=lambda **kwargs: gw,
    ), patch(
        "bosch_thermostat_client.gateway_chooser",
        return_value=lambda **kwargs: gw,
    ):
        yield gw

async def test_sensor_setup(hass, mock_gateway, snapshot):
    """Test sensor setup and states."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "1.1.1.1",
            "uuid": "123456789",
            ACCESS_KEY: "abc",
            ACCESS_TOKEN: "def",
            CONF_DEVICE_TYPE: EASYCONTROL,
            CONF_PROTOCOL: XMPP,
            "verify_ssl": True,
            SENSORS: ["/system/sensors/temperatures/outdoor_t1"],
        },
    )
    entry.add_to_hass(hass)
    
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check states
    state = hass.states.get("sensor.outdoor_t1")
    assert state is not None
    assert state.state == "12.5"
    
    # Snapshot testing
    assert state == snapshot
