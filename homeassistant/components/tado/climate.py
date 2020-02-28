"""Support for Tado thermostats."""
import logging

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MIDDLE,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_HOME,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_TENTHS, TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DOMAIN, SIGNAL_TADO_UPDATE_RECEIVED
from .const import (
    CONST_MODE_COOL,
    CONST_MODE_HEAT,
    CONST_MODE_HEAT_COOL,
    CONST_MODE_OFF,
    CONST_MODE_SMART_SCHEDULE,
    CONST_OVERLAY_MANUAL,
    CONST_OVERLAY_TADO_MODE,
    DATA,
    TYPE_AIR_CONDITIONING,
    TYPE_HEATING,
)

_LOGGER = logging.getLogger(__name__)

HASS_TO_TADO_HVAC_MODE_MAP = {
    HVAC_MODE_OFF: HVAC_MODE_OFF,
    HVAC_MODE_AUTO: CONST_MODE_SMART_SCHEDULE,
    HVAC_MODE_HEAT: CONST_MODE_HEAT,
    HVAC_MODE_COOL: CONST_MODE_COOL,
    HVAC_MODE_HEAT_COOL: CONST_MODE_HEAT_COOL,
}
TADO_TO_HASS_HVAC_MODE_MAP = {
    CONST_MODE_OFF: HVAC_MODE_OFF,
    CONST_MODE_SMART_SCHEDULE: HVAC_MODE_AUTO,
    CONST_MODE_HEAT: HVAC_MODE_HEAT,
    CONST_MODE_COOL: HVAC_MODE_COOL,
    CONST_MODE_HEAT_COOL: HVAC_MODE_HEAT_COOL,
}

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE
SUPPORT_HVAC_HEAT = [HVAC_MODE_HEAT, HVAC_MODE_AUTO, HVAC_MODE_OFF]
SUPPORT_HVAC_COOL = [HVAC_MODE_COOL, HVAC_MODE_AUTO, HVAC_MODE_OFF]
SUPPORT_HVAC_HEAT_COOL = [
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_AUTO,
    HVAC_MODE_OFF,
]
SUPPORT_FAN = [FAN_AUTO, FAN_HIGH, FAN_MIDDLE, FAN_LOW]
SUPPORT_PRESET = [PRESET_AWAY, PRESET_HOME]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tado climate platform."""
    if discovery_info is None:
        return

    api_list = hass.data[DOMAIN][DATA]
    entities = []

    for tado in api_list:
        for zone in tado.zones:
            if zone["type"] in [TYPE_HEATING, TYPE_AIR_CONDITIONING]:
                entity = create_climate_entity(tado, zone["name"], zone["id"])
                if entity:
                    entities.append(entity)

    if entities:
        add_entities(entities, True)


def create_climate_entity(tado, name: str, zone_id: int):
    """Create a Tado climate entity."""
    capabilities = tado.get_capabilities(zone_id)
    _LOGGER.debug("Capabilities for zone %s: %s", zone_id, capabilities)

    zone_type = capabilities["type"]

    ac_support_fanspeeds = False
    ac_support_heat = False
    if zone_type == TYPE_AIR_CONDITIONING:
        # Only use heat if available
        # (you don't have to setup a heat mode, but cool is required)
        # Heat is preferred as it generally has a lower minimum temperature
        if "HEAT" in capabilities:
            temperatures = capabilities["HEAT"]["temperatures"]
            ac_support_heat = True
        else:
            temperatures = capabilities["COOL"]["temperatures"]

        if capabilities["COOL"].get("fanSpeeds"):
            ac_support_fanspeeds = True
    elif "temperatures" in capabilities:
        temperatures = capabilities["temperatures"]
    else:
        _LOGGER.debug("Not adding zone %s since it has no temperature", name)
        return None

    min_temp = float(temperatures["celsius"]["min"])
    max_temp = float(temperatures["celsius"]["max"])
    step = temperatures["celsius"].get("step", PRECISION_TENTHS)

    entity = TadoClimate(
        tado,
        name,
        zone_id,
        zone_type,
        min_temp,
        max_temp,
        step,
        ac_support_heat,
        ac_support_fanspeeds,
    )
    return entity


class TadoClimate(ClimateDevice):
    """Representation of a Tado climate entity."""

    def __init__(
        self,
        tado,
        zone_name,
        zone_id,
        zone_type,
        min_temp,
        max_temp,
        step,
        ac_support_heat,
        ac_support_fanspeeds,
    ):
        """Initialize of Tado climate entity."""
        self._tado = tado

        self.zone_name = zone_name
        self.zone_id = zone_id
        self.zone_type = zone_type
        self._unique_id = f"{zone_type} {zone_id} {tado.device_id}"

        self._ac_device = zone_type == TYPE_AIR_CONDITIONING
        self._ac_support_heat = ac_support_heat
        self._ac_support_fanspeeds = ac_support_fanspeeds

        self._available = False

        self._cur_temp = None
        self._cur_humidity = None
        self._is_away = False
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._step = step
        self._target_temp = None

        self._current_tado_fan_speed = FAN_AUTO
        self._current_tado_hvac_mode = CONST_MODE_SMART_SCHEDULE
        self._current_hvac_action = CONST_MODE_OFF

    async def async_added_to_hass(self):
        """Register for sensor updates."""

        @callback
        def async_update_callback():
            """Schedule an entity update."""
            self.async_schedule_update_ha_state(True)

        async_dispatcher_connect(
            self.hass,
            SIGNAL_TADO_UPDATE_RECEIVED.format("zone", self.zone_id),
            async_update_callback,
        )

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the entity."""
        return self.zone_name

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """Do not poll."""
        return False

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._cur_humidity

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._cur_temp

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        return TADO_TO_HASS_HVAC_MODE_MAP.get(
            self._current_tado_hvac_mode, CURRENT_HVAC_OFF
        )

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        if self._ac_device:
            if self._ac_support_heat:
                return SUPPORT_HVAC_HEAT_COOL
            return SUPPORT_HVAC_COOL
        return SUPPORT_HVAC_HEAT

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        return self._current_hvac_action

    @property
    def fan_mode(self):
        """Return the fan setting."""
        if self._ac_device:
            return self._current_tado_fan_speed
        return None

    @property
    def fan_modes(self):
        """List of available fan modes."""
        if self._ac_device:
            return SUPPORT_FAN
        return None

    def set_fan_mode(self, fan_mode: str):
        """Turn fan on/off."""
        self._control_hvac(fan_mode=fan_mode)

    @property
    def preset_mode(self):
        """Return the current preset mode (home, away)."""
        if self._is_away:
            return PRESET_AWAY
        return PRESET_HOME

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return SUPPORT_PRESET

    def set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        if preset_mode == PRESET_HOME:
            self._tado.set_home()
        else:
            self._tado.set_away()

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._step

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._control_hvac(target_temp=temperature)

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        temperature = None

        # Set a target temperature if we don't have any
        # This can happen when we switch from Off to On
        if self._target_temp is None:
            if self._ac_device:
                temperature = self.max_temp
            else:
                temperature = self.min_temp

        self._control_hvac(
            hvac_mode=HASS_TO_TADO_HVAC_MODE_MAP[hvac_mode], target_temp=temperature
        )

    @property
    def available(self):
        """Return if the device is available."""
        return self._available

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._max_temp

    def update(self):
        """Handle update callbacks."""
        _LOGGER.debug("Updating climate platform for zone %d", self.zone_id)
        data = self._tado.data["zone"][self.zone_id]

        if "sensorDataPoints" in data:
            sensor_data = data["sensorDataPoints"]

            if "insideTemperature" in sensor_data:
                temperature = float(sensor_data["insideTemperature"]["celsius"])
                self._cur_temp = temperature

            if "humidity" in sensor_data:
                humidity = float(sensor_data["humidity"]["percentage"])
                self._cur_humidity = humidity

        if "tadoMode" in data:
            mode = data["tadoMode"]
            self._is_away = mode == "AWAY"

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

            self._current_tado_fan_speed = CONST_MODE_OFF
            if setting["power"] == "ON":
                # If there is no overlay, the mode will always be
                # "SMART_SCHEDULE"
                self._current_tado_hvac_mode = setting["mode"]
                # Not all devices have fans
                self._current_tado_fan_speed = setting.get("fanSpeed", CONST_MODE_OFF)
                self._current_hvac_action = CURRENT_HVAC_IDLE

        if "activityDataPoints" in data:
            activity_data = data["activityDataPoints"]
            if "acPower" in activity_data and activity_data["acPower"] is not None:
                if not activity_data["acPower"]["value"] == "OFF":
                    self._current_hvac_action = CURRENT_HVAC_COOL
            if (
                "heatingPower" in activity_data
                and activity_data["heatingPower"] is not None
            ):
                if float(activity_data["heatingPower"]["percentage"]) > 0.0:
                    self._current_hvac_action = CURRENT_HVAC_HEAT

        self._available = True

    def _control_hvac(self, hvac_mode=None, target_temp=None, fan_mode=None):
        """Send new target temperature to Tado."""

        if hvac_mode:
            self._current_tado_hvac_mode = hvac_mode

        if target_temp:
            self._target_temp = target_temp

        if fan_mode:
            self._fan_mode = fan_mode

        # Set optimistically
        self.schedule_update_ha_state()

        if self._current_tado_hvac_mode == CONST_MODE_SMART_SCHEDULE:
            _LOGGER.debug(
                "Switching to SMART_SCHEDULE for zone %s (%d)",
                self.zone_name,
                self.zone_id,
            )
            self._tado.reset_zone_overlay(self.zone_id)
            return

        if self._current_tado_hvac_mode == CONST_MODE_OFF:
            _LOGGER.debug(
                "Switching to OFF for zone %s (%d)", self.zone_name, self.zone_id
            )
            self._tado.set_zone_off(self.zone_id, CONST_OVERLAY_MANUAL, self.zone_type)
            return

        _LOGGER.debug(
            "Switching to %s for zone %s (%d) with temperature %s °C",
            self._current_tado_hvac_mode,
            self.zone_name,
            self.zone_id,
            self._target_temp,
        )

        if self._tado.fallback:
            # Fallback to Smart Schedule at next Schedule switch
            self._default_overlay = CONST_OVERLAY_TADO_MODE
        else:
            # Don't fallback to Smart Schedule, but keep in manual mode
            self._default_overlay = CONST_OVERLAY_MANUAL

        self._tado.set_zone_overlay(
            zone_id=self.zone_id,
            overlay_mode=CONST_OVERLAY_TADO_MODE
            if self._tado.fallback
            else CONST_OVERLAY_MANUAL,  # What to do when the period ends
            temperature=self._target_temp,
            duration=None,
            device_type=self.zone_type,
            mode=self._current_tado_hvac_mode,
            fan_speed=(
                self._fan_mode if self._ac_support_fanspeeds else None
            ),  # api defaults to not sending fanSpeed if not specified
        )
