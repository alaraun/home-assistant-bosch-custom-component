"""Test the Bosch thermostat config flow."""
from unittest.mock import patch, MagicMock
import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_PASSWORD,
    CONF_ACCESS_TOKEN,
    CONF_VERIFY_SSL,
)
from bosch_thermostat_client.const import HTTP, XMPP
from bosch_thermostat_client.const.ivt import IVT
from bosch_thermostat_client.const.easycontrol import EASYCONTROL
from custom_components.bosch.const import (
    DOMAIN,
    ACCESS_KEY,
    ACCESS_TOKEN,
    CONF_DEVICE_TYPE,
    CONF_PROTOCOL,
    UUID,
)
from tests.common import MockGateway

@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "custom_components.bosch.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup

async def test_form_http(hass, mock_setup_entry):
    """Test we get the form and handle HTTP protocol for IVT."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "choose_type"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_DEVICE_TYPE: IVT},
    )
    assert result["step_id"] == "protocol"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PROTOCOL: HTTP},
    )
    assert result["step_id"] == "http_config"

    # Patch in config_flow.py directly
    with patch(
        "custom_components.bosch.config_flow.gateway_chooser",
        return_value=MockGateway,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ADDRESS: "1.1.1.1",
                CONF_ACCESS_TOKEN: "def",
                CONF_PASSWORD: "ghi",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bosch Gateway"
    assert result["data"] == {
        CONF_ADDRESS: "1.1.1.1",
        UUID: "123456789",
        ACCESS_KEY: "abc",
        ACCESS_TOKEN: "def",
        CONF_DEVICE_TYPE: IVT,
        CONF_PROTOCOL: HTTP,
        CONF_VERIFY_SSL: True,
    }

async def test_form_invalid_auth(hass):
    """Test we handle invalid auth."""
    from bosch_thermostat_client.exceptions import EncryptionException

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_DEVICE_TYPE: IVT},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PROTOCOL: HTTP},
    )

    with patch(
        "custom_components.bosch.config_flow.gateway_chooser",
        side_effect=EncryptionException("Wrong credentials"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ADDRESS: "1.1.1.1",
                CONF_ACCESS_TOKEN: "def",
                CONF_PASSWORD: "ghi",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "faulty_credentials"

async def test_options_flow(hass):
    """Test the options flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry
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
        options={
            "new_stats_api": False,
            "optimistic_mode": False,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "new_stats_api": True,
            "optimistic_mode": True,
            "scan_interval": 120,
            "concurrency": 5,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "new_stats_api": True,
        "optimistic_mode": True,
        "scan_interval": 120,
        "concurrency": 5,
    }
