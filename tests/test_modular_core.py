"""Tests for Phase 7/7.1 modularization and typing refactor."""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from datetime import datetime, timedelta
from custom_components.bosch.coordinator import BoschDataUpdateCoordinator
from custom_components.bosch.sensor.recording import RecordingSensor
from custom_components.bosch.sensor.energy import EnergySensor
from custom_components.bosch.bosch_entity import BoschEntity
from custom_components.bosch.const import (
    DOMAIN,
    ACCESS_KEY,
    ACCESS_TOKEN,
    CONF_DEVICE_TYPE,
    CONF_PROTOCOL,
    SENSORS,
    BOSCH_GATEWAY_ENTRY,
)
from bosch_thermostat_client.const import RECORDING, XMPP
from bosch_thermostat_client.const.easycontrol import EASYCONTROL
from homeassistant.const import CONF_ADDRESS
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.common import MockGateway, MockEntity
import homeassistant.helpers.device_registry as dr

@pytest.fixture
def mock_hass_data():
    return {DOMAIN: {"uuid": {}}}

@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock(spec=BoschDataUpdateCoordinator)
    coordinator.uuid = "uuid"
    coordinator._semaphore = asyncio.Semaphore(1)
    return coordinator

@pytest.fixture
def mock_gateway():
    gateway = MagicMock()
    gateway.device_model = "model"
    gateway.device_type = "type"
    gateway.firmware = "firmware"
    return gateway

@pytest.fixture
def mock_bosch_object():
    obj = MagicMock()
    obj.name = "Test Object"
    obj.id = "test_id"
    obj.parent_id = "parent_id"
    obj.device_class = "energy"
    obj.state_class = "total_increasing"
    obj.fetch_range = AsyncMock(return_value=[{"d": datetime.now(), "value": 10}])
    obj.fetch_all = AsyncMock(return_value={"01-01-2026": {"value": 100}})
    return obj

@pytest.mark.asyncio
async def test_modular_services_registration(hass):
    """Test that modularized services are registered and callable."""
    gw = MockGateway()
    gw.sensors = [MockEntity(id="/test/uri", name="Test", value=10)]
    gw.raw_query = AsyncMock(return_value={"status": "ok"})
    
    with patch(
        "bosch_thermostat_client.gateway_chooser",
        return_value=lambda **kwargs: gw,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ADDRESS: "1.1.1.1",
                "uuid": "123456789",
                ACCESS_KEY: "abc",
                ACCESS_TOKEN: "def",
                CONF_DEVICE_TYPE: EASYCONTROL,
                CONF_PROTOCOL: XMPP,
            },
            entry_id="bosch_entry",
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Check if services are registered
        assert hass.services.has_service(DOMAIN, "debug_scan")
        assert hass.services.has_service(DOMAIN, "send_custom_get")

        # Test send_custom_get service
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, "123456789")},
        )
        
        result = await hass.services.async_call(
            DOMAIN,
            "send_custom_get",
            {"device_id": [device.id], "path": "/test/uri"},
            blocking=True,
            return_response=True,
        )
        
        assert result["data"] == [{"status": "ok"}]
        gw.raw_query.assert_called_with(path="/test/uri")

@pytest.mark.asyncio
async def test_bosch_entity_device_info(mock_coordinator, mock_bosch_object, mock_gateway):
    """Test DeviceInfo has correct 2-tuple identifiers."""
    mock_coordinator.hass = MagicMock()
    entity = BoschEntity(
        coordinator=mock_coordinator,
        bosch_object=mock_bosch_object,
        gateway=mock_gateway,
        uuid="uuid"
    )
    
    device_info = entity.device_info
    identifiers = list(device_info["identifiers"])
    assert len(identifiers) == 1
    assert len(identifiers[0]) == 2
    assert identifiers[0][0] == DOMAIN
    assert identifiers[0][1] == "uuid_parent_id"

@pytest.mark.asyncio
async def test_recording_sensor_chunked_fetch(mock_coordinator, mock_bosch_object, mock_gateway):
    """Test RecordingSensor._insert_statistics uses 7-day chunks."""
    with patch("custom_components.bosch.sensor.recording.RecordingSensor.statistic_id", new_callable=PropertyMock) as mock_stat_id:
        mock_stat_id.return_value = "recording_stats"
        mock_coordinator.hass = MagicMock()
        sensor = RecordingSensor(
            coordinator=mock_coordinator,
            uuid="uuid",
            bosch_object=mock_bosch_object,
            gateway=mock_gateway,
            name="test",
            attr_uri="uri",
            new_stats_api=True
        )
        sensor.entity_id = "sensor.test"
        
        # Mock get_last_stat to return empty (triggering full 30-day fetch)
        sensor.get_last_stat = AsyncMock(return_value={})
        sensor.append_statistics = MagicMock(return_value=100.0)
        
        with patch("custom_components.bosch.sensor.recording.dt_util.now", return_value=datetime(2026, 3, 16)):
            await sensor._insert_statistics()
        
        # Should call fetch_past_data 5 times
        assert mock_bosch_object.fetch_range.call_count == 5

@pytest.mark.asyncio
async def test_energy_sensor_chunked_fetch(mock_coordinator, mock_bosch_object, mock_gateway):
    """Test EnergySensor._insert_statistics uses 7-day chunks."""
    with patch("custom_components.bosch.sensor.energy.EnergySensor.statistic_id", new_callable=PropertyMock) as mock_stat_id:
        mock_stat_id.return_value = "energy_stats"
        mock_coordinator.hass = MagicMock()
        sensor = EnergySensor(
            coordinator=mock_coordinator,
            uuid="uuid",
            bosch_object=mock_bosch_object,
            gateway=mock_gateway,
            sensor_attributes={"attr": "CH", "name": "Energy"},
            attr_uri="uri",
            new_stats_api=True
        )
        sensor.entity_id = "sensor.energy"
        
        sensor.get_last_stat = AsyncMock(return_value={})
        sensor.append_statistics = MagicMock(return_value=500.0)
        
        with patch("custom_components.bosch.sensor.energy.dt_util.now", return_value=datetime(2026, 3, 16)):
            await sensor._insert_statistics()
        
        # Should call fetch_range 5 times
        assert mock_bosch_object.fetch_range.call_count == 5
