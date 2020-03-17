"""The MyQ integration."""
from homeassistant.const import STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING

DOMAIN = "myq"

PLATFORMS = ["cover"]


MYQ_TO_HASS = {
    "closed": STATE_CLOSED,
    "closing": STATE_CLOSING,
    "open": STATE_OPEN,
    "opening": STATE_OPENING,
}

GATE_STATE_ICONS = {
    STATE_CLOSED: "mdi:garage",
    STATE_CLOSING: "mdi:garage",
    STATE_OPENING: "mdi:garage-open",
    STATE_OPEN: "mdi:garage-open",
}

GARAGE_STATE_ICONS = {
    STATE_CLOSED: "mdi:gate",
    STATE_CLOSING: "mdi:gate-arrow-right",
    STATE_OPENING: "mdi:gate-arrow-right",
    STATE_OPEN: "mdi:gate-open",
}
