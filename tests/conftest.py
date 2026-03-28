"""Global fixtures for Bosch integration tests."""
import pytest
from syrupy.assertion import SnapshotAssertion
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension

@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield
