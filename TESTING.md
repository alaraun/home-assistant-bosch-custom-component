# Testing the Bosch Home Assistant Integration

This project uses `pytest` along with `pytest-homeassistant-custom-component` for integration testing.

## Setup

1. Create a virtual environment:
   ```bash
   uv venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   uv pip install -r tests/requirements.txt
   ```

## Running Tests

Run all tests:
```bash
pytest
```

Run a specific test file:
```bash
pytest tests/test_sensor.py
```

## Snapshot Testing

This project uses `syrupy` for snapshot testing of entity states. 

To update snapshots:
```bash
pytest --snapshot-update
```

## Mocking

We use a `MockGateway` (defined in `tests/common.py`) to simulate the `bosch-thermostat-client-python` library. Fixtures for different device types are stored in `.planning/phases/05-testing-foundation/fixtures/`.
