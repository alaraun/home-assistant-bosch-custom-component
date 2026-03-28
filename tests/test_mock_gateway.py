"""Test the MockGateway helper."""
import pytest
from tests.common import MockGateway, load_fixture

@pytest.mark.asyncio
async def test_mock_gateway_init():
    """Test MockGateway initialization."""
    gateway = MockGateway(host="1.1.1.1", access_token="abc")
    assert gateway.host == "1.1.1.1"
    assert gateway.access_token == "abc"
    
    async with gateway as gw:
        assert await gw.check_connection() == "123456789"

def test_load_fixture():
    """Test loading a fixture."""
    data = load_fixture("easycontrol")
    assert "/gateway/uuid" in data
    assert data["/gateway/uuid"]["value"] == "123456789"
