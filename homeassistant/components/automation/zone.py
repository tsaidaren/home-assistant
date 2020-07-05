"""Offer zone automation rules."""
import voluptuous as vol

from homeassistant.const import CONF_ENTITY_ID, CONF_EVENT, CONF_PLATFORM, CONF_ZONE
from homeassistant.core import callback
from homeassistant.helpers import condition, config_validation as cv, location
from homeassistant.helpers.event import async_track_state_change

# mypy: allow-untyped-defs, no-check-untyped-defs

EVENT_ENTER = "enter"
EVENT_LEAVE = "leave"
DEFAULT_EVENT = EVENT_ENTER

TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLATFORM): "zone",
        vol.Required(CONF_ENTITY_ID): cv.entity_ids,
        vol.Required(CONF_ZONE): cv.entity_id,
        vol.Required(CONF_EVENT, default=DEFAULT_EVENT): vol.Any(
            EVENT_ENTER, EVENT_LEAVE
        ),
    }
)


async def async_attach_trigger(hass, config, action, automation_info):
    """Listen for state changes based on configuration."""
    entity_id = config.get(CONF_ENTITY_ID)
    zone_entity_id = config.get(CONF_ZONE)
    event = config.get(CONF_EVENT)

    @callback
    def zone_automation_listener(entity, from_s, to_s):
        """Listen for state changes and calls action."""
        if (
            from_s
            and not location.has_location(from_s)
            or not location.has_location(to_s)
        ):
            return

        zone_state = hass.states.get(zone_entity_id)
        from_match = condition.zone(hass, zone_state, from_s) if from_s else False
        to_match = condition.zone(hass, zone_state, to_s)

        if (
            event == EVENT_ENTER
            and not from_match
            and to_match
            or event == EVENT_LEAVE
            and from_match
            and not to_match
        ):
            hass.async_run_job(
                action(
                    {
                        "trigger": {
                            "platform": "zone",
                            "entity_id": entity,
                            "from_state": from_s,
                            "to_state": to_s,
                            "zone": zone_state,
                            "event": event,
                        }
                    },
                    context=to_s.context,
                )
            )

    return async_track_state_change(hass, entity_id, zone_automation_listener)
