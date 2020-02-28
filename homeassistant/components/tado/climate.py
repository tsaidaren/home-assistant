"""Support for Tado thermostats."""
import logging

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_HOME,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_TENTHS, TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DOMAIN, SIGNAL_TADO_UPDATE_RECEIVED
from .const import (
    CONST_FAN_AUTO,
    CONST_MODE_AUTO,
    CONST_MODE_COOL,
    CONST_MODE_DRY,
    CONST_MODE_FAN,
    CONST_MODE_HEAT,
    CONST_MODE_OFF,
    CONST_MODE_SMART_SCHEDULE,
    CONST_OVERLAY_MANUAL,
    CONST_OVERLAY_TADO_MODE,
    DATA,
    TYPE_AIR_CONDITIONING,
    TYPE_HEATING,
)

_LOGGER = logging.getLogger(__name__)

KNOWN_TADO_OPTIONAL_MODES = [
    CONST_MODE_AUTO,
    CONST_MODE_HEAT,
    CONST_MODE_COOL,
    CONST_MODE_DRY,
    CONST_MODE_FAN,
]

HA_TO_TADO_HVAC_MODE_MAP = {
    HVAC_MODE_OFF: CONST_MODE_OFF,
    HVAC_MODE_HEAT_COOL: CONST_MODE_SMART_SCHEDULE,
    HVAC_MODE_AUTO: CONST_MODE_AUTO,
    HVAC_MODE_HEAT: CONST_MODE_HEAT,
    HVAC_MODE_COOL: CONST_MODE_COOL,
    HVAC_MODE_DRY: CONST_MODE_DRY,
    HVAC_MODE_FAN_ONLY: CONST_MODE_FAN,
}

TADO_TO_HA_HVAC_MODE_MAP = {
    value: key for key, value in HA_TO_TADO_HVAC_MODE_MAP.items()
}

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

    # 'type': 'AIR_CONDITIONING', 'AUTO': {}, 'COOL': {'temperatures': {'celsius': {'min': 18, 'max': 31, 'step': 1.0}, 'fahrenheit': {'min': 64, 'max': 88, 'step': 1.0}}, 'fanSpeeds': ['AUTO', 'HIGH', 'MIDDLE', 'LOW']}, 'DRY': {}, 'FAN': {}, 'HEAT': {'temperatures': {'celsius': {'min': 16, 'max': 30, 'step': 1.0}, 'fahrenheit': {'min': 61, 'max': 86, 'step': 1.0}}, 'fanSpeeds': ['AUTO', 'HIGH', 'MIDDLE', 'LOW']}}

    zone_type = capabilities["type"]
    support_flags = SUPPORT_PRESET_MODE | SUPPORT_TARGET_TEMPERATURE
    supported_hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_HEAT_COOL]
    supported_fan_modes = []

    if zone_type == TYPE_AIR_CONDITIONING:
        # Only use heat if available
        # (you don't have to setup a heat mode, but cool is required)
        # Heat is preferred as it generally has a lower minimum temperature
        for mode in KNOWN_TADO_OPTIONAL_MODES:
            if mode in capabilities:
                supported_hvac_modes.push(TADO_TO_HA_HVAC_MODE_MAP[mode])

        if capabilities["COOL"].get("fanSpeeds"):
            support_flags |= SUPPORT_FAN_MODE
            supported_fan_modes = capabilities["COOL"].get("fanSpeeds")
    else:
        supported_hvac_modes.push(HVAC_MODE_HEAT)

    if "temperatures" in capabilities:
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
        supported_hvac_modes,
        supported_fan_modes,
        support_flags,
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
        supported_hvac_modes,
        supported_fan_modes,
        support_flags,
    ):
        """Initialize of Tado climate entity."""
        self._tado = tado

        self.zone_name = zone_name
        self.zone_id = zone_id
        self.zone_type = zone_type
        self._unique_id = f"{zone_type} {zone_id} {tado.device_id}"

        self._ac_device = zone_type == TYPE_AIR_CONDITIONING
        self._supported_hvac_modes = supported_hvac_modes
        self._supported_fan_modes = supported_fan_modes
        self._support_flags = support_flags

        self._available = False

        self._cur_temp = None
        self._cur_humidity = None
        self._is_away = False
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._step = step
        self._target_temp = None

        self._current_tado_fan_speed = CONST_FAN_AUTO
        self._current_tado_hvac_mode = CONST_MODE_SMART_SCHEDULE
        self._current_hvac_action = CURRENT_HVAC_OFF

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
        return self._support_flags

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
        return TADO_TO_HA_HVAC_MODE_MAP.get(
            self._current_tado_hvac_mode, CURRENT_HVAC_OFF
        )

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return self._supported_fan_modes

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
        return self._supported_fan_modes

    def set_current_tado_fan_speed(self, fan_mode: str):
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
            hvac_mode=HA_TO_TADO_HVAC_MODE_MAP[hvac_mode], target_temp=temperature
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
                    # acPower means the unit has power. It could
                    # be a heat pump so if the mode is set to heat
                    # we have to assume its heating
                    if self._current_tado_hvac_mode == CONST_MODE_HEAT:
                        self._current_hvac_action = CURRENT_HVAC_HEAT
                    else:
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
            self._current_tado_fan_speed = fan_mode

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

        # Don't fallback to Smart Schedule, but keep in manual mode
        overlay_mode = CONST_OVERLAY_MANUAL
        if self._tado.fallback:
            # Fallback to Smart Schedule at next Schedule switch
            overlay_mode = CONST_OVERLAY_TADO_MODE

        temperature = self._target_temp
        if self._current_tado_hvac_mode == CONST_MODE_AUTO:
            # A temperature cannot be passed with CONST_MODE_AUTO "Auto"
            temperature = None

        self._tado.set_zone_overlay(
            zone_id=self.zone_id,
            overlay_mode=overlay_mode,  # What to do when the period ends
            temperature=temperature,
            duration=None,
            device_type=self.zone_type,
            mode=self._current_tado_hvac_mode,
            fan_speed=(
                self._current_tado_fan_speed if self._ac_support_fanspeeds else None
            ),  # api defaults to not sending fanSpeed if not specified
        )
