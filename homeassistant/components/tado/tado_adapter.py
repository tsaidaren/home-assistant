import logging

from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
)

from .const import (
    CONST_FAN_AUTO,
    CONST_FAN_OFF,
    CONST_MODE_SMART_SCHEDULE,
    TADO_MODES_TO_HA_CURRENT_HVAC_ACTION,
)

_LOGGER = logging.getLogger(__name__)


class TadoZoneData:
    def __init__(self, data):
        self._data = data
        self._cur_temp = None
        self._connection = None
        self._cur_temp_timestamp = None
        self._cur_humidity = None
        self._is_away = False
        self._current_hvac_action = None
        self._current_tado_fan_speed = None
        self._current_tado_hvac_mode = None
        self._target_temp = None
        self._available = False
        self._power = None
        self._link = None
        self._ac_power_timestamp = None
        self._heating_power_timestamp = None
        self._ac_power = None
        self._heating_power = None
        self._heating_power_percentage = None
        self._tado_mode = None
        self._overlay_active = None
        self._overlay_termination_type = None
        self._preparation = None
        self._open_window = None
        self.update_data(data)

    @property
    def preparation(self):
        return self._preparation

    def open_window(self):
        return self._open_window

    @property
    def current_temp(self):
        return self._cur_temp

    @property
    def current_temp_timestamp(self):
        return self._cur_temp_timestamp

    @property
    def connection(self):
        return self._connection

    @property
    def tado_mode(self):
        return self._tado_mode

    @property
    def overlay_active(self):
        return self._current_tado_hvac_mode != CONST_MODE_SMART_SCHEDULE

    def overlay_termination_type(self):
        return self._overlay_termination

    @property
    def current_humidity(self):
        return self._cur_humidity

    @property
    def current_humidity_timestamp(self):
        return self._cur_humidity_timestamp

    @property
    def ac_power_timestamp(self):
        return self._ac_power_timestamp

    @property
    def heating_power_timestamp(self):
        return self._heating_power_timestamp

    @property
    def ac_power(self):
        return self._ac_power

    @property
    def heating_power(self):
        return self._heating_power

    @property
    def heating_power_percentage(self):
        return self._heating_power_percentage

    @property
    def is_away(self):
        return self._is_away

    @property
    def power(self):
        return self._power

    @property
    def current_hvac_action(self):
        return self._current_hvac_action

    @property
    def current_tado_fan_speed(self):
        return self._current_tado_fan_speed

    @property
    def link(self):
        return self._link

    @property
    def current_tado_hvac_mode(self):
        return self._current_tado_hvac_mode

    @property
    def target_temp(self):
        return self._target_temp

    @property
    def available(self):
        return self._available

    def update_data(self, data):
        """Handle update callbacks."""
        _LOGGER.debug("Updating climate platform for zone %d", self.zone_id)
        if "sensorDataPoints" in data:
            sensor_data = data["sensorDataPoints"]

            if "insideTemperature" in sensor_data:
                temperature = float(sensor_data["insideTemperature"]["celsius"])
                self._cur_temp = temperature
                self._cur_temp_timestamp = sensor_data["insideTemperature"]["timestamp"]

            if "humidity" in sensor_data:
                humidity = float(sensor_data["humidity"]["percentage"])
                self._cur_humidity = humidity
                self._cur_humidity_timestamp = sensor_data["humidity"]["timestamp"]

        if "tadoMode" in data:
            mode = data["tadoMode"]
            self._is_away = mode == "AWAY"
            self._tado_mode = data["tadoMode"]

        if "link" in data:
            self._link = data["link"]["state"]

        self._current_hvac_action = CURRENT_HVAC_OFF

        if "setting" in data:
            # temperature setting will not exist when device is off
            if (
                "temperature" in data["setting"]
                and data["setting"]["temperature"] is not None
            ):
                setting = float(data["setting"]["temperature"]["celsius"])
                self._target_temp = setting

            setting = data["setting"]

            self._current_tado_fan_speed = CONST_FAN_OFF
            self._power = setting["power"]
            if setting["power"] == "ON":
                # If there is no overlay, the mode will always be
                # "SMART_SCHEDULE"
                self._current_tado_hvac_mode = setting["mode"]
                # Not all devices have fans
                self._current_tado_fan_speed = setting.get("fanSpeed", CONST_FAN_AUTO)
                self._current_hvac_action = CURRENT_HVAC_IDLE

        # If there is no overlay
        # then we are running the smart schedule
        self._overlay_termination_time = None
        if "overlay" in data and data["overlay"] is None:
            self._current_tado_hvac_mode = CONST_MODE_SMART_SCHEDULE
            self._overlay_termination_time = data["overlay"]["termination"]["type"]

        self._preparation = data["preparation"] is not None
        self._open_window = "openWindow" in data and data["openWindow"]

        if "activityDataPoints" in data:
            activity_data = data["activityDataPoints"]
            if "acPower" in activity_data and activity_data["acPower"] is not None:
                self._ac_power = activity_data["acPower"]["value"]
                self._ac_power_timestamp = activity_data["acPower"]["timestamp"]
                if activity_data["acPower"]["value"] == "OFF":
                    self._current_hvac_action = CURRENT_HVAC_OFF
                else:
                    # acPower means the unit has power so we need to map the mode
                    self._current_hvac_action = TADO_MODES_TO_HA_CURRENT_HVAC_ACTION.get(
                        self._current_tado_hvac_mode, CURRENT_HVAC_COOL
                    )
            if (
                "heatingPower" in activity_data
                and activity_data["heatingPower"] is not None
            ):
                self._heating_power = activity_data["heatingPower"]["value"]
                self._heating_power_timestamp = activity_data["heatingPower"][
                    "timestamp"
                ]
                self._heating_power_percentage = float(
                    activity_data["heatingPower"]["percentage"]
                )

                if self._heating_power_percentage > 0.0:
                    self._current_hvac_action = CURRENT_HVAC_HEAT

        if "connectionState" in data:
            self._connection = data["connectionState"]["value"]

        self._available = True
