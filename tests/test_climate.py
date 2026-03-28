"""Test the Bosch climate platform."""
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
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.common import MockGateway, MockClimate

@pytest.fixture
def mock_gateway():
    """Mock Bosch Gateway."""
    gw = MockGateway()
    gw.heating_circuits = [
        MockClimate(id="/heatingCircuits/hc1", name="hc1")
    ]
    
    with patch(
        "custom_components.bosch.config_flow.gateway_chooser",
        return_value=lambda **kwargs: gw,
    ), patch(
        "bosch_thermostat_client.gateway_chooser",
        return_value=lambda **kwargs: gw,
    ):
        yield gw

async def test_climate_setup(hass, mock_gateway, snapshot):
    """Test climate setup and states."""
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
        },
    )
    entry.add_to_hass(hass)
    
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check states
    state = hass.states.get("climate.hc1")
    assert state is not None
    assert state.state == "heat"
    assert state.attributes["current_temperature"] == 21.0
    
    # Snapshot testing
    assert state == snapshot
