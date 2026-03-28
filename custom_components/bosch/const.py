"""Constants for the bosch component."""
from datetime import timedelta

import voluptuous as vol
from bosch_thermostat_client.const import DHW, HC, SC, ZN
from bosch_thermostat_client.const.easycontrol import DV
from homeassistant.const import UnitOfEnergy, UnitOfTemperature, UnitOfTime

DOMAIN = "bosch"
BOSCH_GATEWAY_ENTRY = "BoschGatewayEntry"
ACCESS_KEY = "access_key"
ACCESS_TOKEN = "access_token"
UUID = "uuid"

CONF_PROTOCOL = "http_xmpp"
CONF_DEVICE_TYPE = "device_type"

GATEWAY = "gateway"
CLIMATE = "climate"
SENSOR = "sensor"
SOLAR = "solar"
WATER_HEATER = "water_heater"
BINARY_SENSOR = "binary_sensor"
SWITCH = "switch"
SELECT = "select"
NUMBER = "number"
VALUE = "value"

SIGNAL_BOSCH = "bosch_signal"
DEFAULT_MIN_TEMP = 0
DEFAULT_MAX_TEMP = 100

BOSCH_STATE = "bosch_state"

START = "start"
STOP = "stop"
SERVICE_CHARGE_SCHEMA = {vol.Optional(VALUE): vol.In([START, STOP])}

SERVICE_CHARGE_START = "set_dhw_charge"
SERVICE_PUT_STRING = "send_custom_put_string"
SERVICE_PUT_FLOAT = "send_custom_put_float"
SERVICE_GET = "send_custom_get"
SERVICE_DEBUG = "debug_scan"
SERVICE_UPDATE = "update_gateway"
RECORDING_SERVICE_UPDATE = "update_recordings_sensor"
SERVICE_MOVE_OLD_DATA = "move_old_statistic_data"

SENSORS = "sensors"
SWITCHPOINT = "switchPoint"
CHARGE = "charge"
MINS = "mins"
WORKING_TIME = "totalWorkingTime"


UNITS_CONVERTER = {
    "C": UnitOfTemperature.CELSIUS,
    UnitOfTemperature.CELSIUS: UnitOfTemperature.CELSIUS,
    "F": UnitOfTemperature.FAHRENHEIT,
    UnitOfTemperature.FAHRENHEIT: UnitOfTemperature.FAHRENHEIT,
    "%": "%",
    "l/min": "l/min",
    "l/h": "l/h",
    "kg/l": "kg/l",
    "mins": MINS,
    "kW": "kW",
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
    "Wh": "Wh",
    "Pascal": "Pascal",
    "bar": "bar",
    "µA": "µA",
    " ": None,
}

NOTIFICATION_ID = "bosch_notification"
SCAN_INTERVAL = timedelta(seconds=60)
FIRMWARE_SCAN_INTERVAL = timedelta(hours=4)
SCAN_SENSOR_INTERVAL = timedelta(seconds=120)

CIRCUITS = [DHW, HC, SC, ZN, DV]
CIRCUITS_SENSOR_NAMES = {
    DHW: "Water heater",
    HC: "Heating circuit",
    SC: "Solar circuit",
    ZN: "Zone circuit",
    DV: "Device",
}

LAST_RESET = "last_reset"

SUPPORTED_PLATFORMS = {
    HC: [CLIMATE],
    DHW: [WATER_HEATER],
    SWITCH: [SWITCH],
    SELECT: [SELECT],
    NUMBER: [NUMBER],
    SC: [SENSOR],
    SENSOR: [SENSOR, BINARY_SENSOR],
    ZN: [CLIMATE],
    DV: [SENSOR],
}

PLATFORM_TO_BOSCH_MAP = {
    SENSOR: "sensors",
    BINARY_SENSOR: "binary_sensors",
    CLIMATE: "climate_circuits",
    WATER_HEATER: "dhw_circuits",
    SWITCH: "switches",
    NUMBER: "numbers",
}
