"""Support for Tado sensors for each zone."""
import logging

from homeassistant.const import TEMP_CELSIUS, UNIT_PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from . import DATA, DOMAIN, SIGNAL_TADO_UPDATE_RECEIVED
from .const import TYPE_AIR_CONDITIONING, TYPE_HEATING, TYPE_HOT_WATER
from .tado_adapter import TadoZoneData

_LOGGER = logging.getLogger(__name__)

ZONE_SENSORS = {
    TYPE_HEATING: [
        "temperature",
        "humidity",
        "power",
        "link",
        "heating",
        "tado mode",
        "overlay",
        "early start",
        "open window",
    ],
    TYPE_AIR_CONDITIONING: [
        "temperature",
        "humidity",
        "power",
        "link",
        "ac",
        "tado mode",
        "overlay",
    ],
    TYPE_HOT_WATER: ["power", "link", "tado mode", "overlay"],
}

DEVICE_SENSORS = ["tado bridge status"]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    api_list = hass.data[DOMAIN][DATA]

    entities = []

    for tado in api_list:
        # Create zone sensors

        for zone in tado.zones:
            entities.extend(
                [
                    create_zone_sensor(tado, zone["name"], zone["id"], variable)
                    for variable in ZONE_SENSORS.get(zone["type"])
                ]
            )

        # Create device sensors
        for home in tado.devices:
            entities.extend(
                [
                    create_device_sensor(tado, home["name"], home["id"], variable)
                    for variable in DEVICE_SENSORS
                ]
            )

    add_entities(entities, True)


def create_zone_sensor(tado, name, zone_id, variable):
    """Create a zone sensor."""
    return TadoSensor(tado, name, "zone", zone_id, variable)


def create_device_sensor(tado, name, device_id, variable):
    """Create a device sensor."""
    return TadoSensor(tado, name, "device", device_id, variable)


class TadoSensor(Entity):
    """Representation of a tado Sensor."""

    def __init__(self, tado, zone_name, sensor_type, zone_id, zone_variable):
        """Initialize of the Tado Sensor."""
        self._tado = tado

        self.zone_name = zone_name
        self.zone_id = zone_id
        self.zone_variable = zone_variable
        self.sensor_type = sensor_type

        self._unique_id = f"{zone_variable} {zone_id} {tado.device_id}"

        self._state = None
        self._state_attributes = None
        self._tado_zone_data = None

    async def async_added_to_hass(self):
        """Register for sensor updates."""

        @callback
        def async_update_callback():
            """Schedule an entity update."""
            self.async_schedule_update_ha_state(True)

        async_dispatcher_connect(
            self.hass,
            SIGNAL_TADO_UPDATE_RECEIVED.format(self.sensor_type, self.zone_id),
            async_update_callback,
        )

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.zone_name} {self.zone_variable}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._state_attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self.zone_variable == "temperature":
            return self.hass.config.units.temperature_unit
        if self.zone_variable == "humidity":
            return UNIT_PERCENTAGE
        if self.zone_variable == "heating":
            return UNIT_PERCENTAGE
        if self.zone_variable == "ac":
            return ""

    @property
    def icon(self):
        """Icon for the sensor."""
        if self.zone_variable == "temperature":
            return "mdi:thermometer"
        if self.zone_variable == "humidity":
            return "mdi:water-percent"

    @property
    def should_poll(self) -> bool:
        """Do not poll."""
        return False

    def update(self):
        """Handle update callbacks."""
        try:
            data = self._tado.data[self.sensor_type][self.zone_id]
        except KeyError:
            return

        self._tado_zone_data = TadoZoneData(data)
        unit = TEMP_CELSIUS

        if self.zone_variable == "temperature":
            self._state = self.hass.config.units.temperature(
                self._tado_zone_data.current_temp, unit
            )
            self._state_attributes = {
                "time": self._tado_zone_data.current_temp_timestamp,
                "setting": 0,  # setting is used in climate device
            }

        elif self.zone_variable == "humidity":
            self._state = self._tado_zone_data.current_humidity
            self._state_attributes = {
                "time": self._tado_zone_data.current_humidity_timestamp
            }

        elif self.zone_variable == "power":
            self._state = self._tado_zone_data.power

        elif self.zone_variable == "link":
            self._state = self._tado_zone_data.link

        elif self.zone_variable == "heating":
            self._state = self._tado_zone_data.heating_power_percentage
            self._state_attributes = {
                "time": self._tado_zone_data.heating_power_timestamp
            }

        elif self.zone_variable == "ac":
            self._state = self._tado_zone_data.ac_power
            self._state_attributes = {"time": self._tado_zone_data.ac_power_timestamp}

        elif self.zone_variable == "tado bridge status":
            self._state = self._tado_zone_data.connection

        elif self.zone_variable == "tado mode":
            self._state = self._tado_zone_data.tado_mode

        elif self.zone_variable == "overlay":
            self._state = self._tado_zone_data.overlay_active
            self._state_attributes = (
                {"termination": self._tado_zone_data.overlay_termination_type}
                if self._state
                else {}
            )

        elif self.zone_variable == "early start":
            self._state = self._tado_zone_data.preparation is not None

        elif self.zone_variable == "open window":
            self._state = self._tado_zone_data.open_window is not None
            self._state_attributes = (
                self._tado_zone_data.open_window if self._state else {}
            )
