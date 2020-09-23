"""Message templates for websocket commands."""

from functools import lru_cache
import logging
from typing import Any, Dict
import zlib

import voluptuous as vol

from homeassistant.core import Event
from homeassistant.helpers import config_validation as cv
from homeassistant.util.json import (
    find_paths_unserializable_data,
    format_unserializable_data,
)

from . import const

_LOGGER = logging.getLogger(__name__)
# mypy: allow-untyped-defs

# Minimal requirements of a message
MINIMAL_MESSAGE_SCHEMA = vol.Schema(
    {vol.Required("id"): cv.positive_int, vol.Required("type"): cv.string},
    extra=vol.ALLOW_EXTRA,
)

# Base schema to extend by message handlers
BASE_COMMAND_MESSAGE_SCHEMA = vol.Schema({vol.Required("id"): cv.positive_int})

DEFLATE_TAIL = bytes([0x00, 0x00, 0xFF, 0xFF])


def result_message(iden: int, result: Any = None) -> Dict:
    """Return a success result message."""
    return {"id": iden, "type": const.TYPE_RESULT, "success": True, "result": result}


def error_message(iden: int, code: str, message: str) -> Dict:
    """Return an error result message."""
    return {
        "id": iden,
        "type": const.TYPE_RESULT,
        "success": False,
        "error": {"code": code, "message": message},
    }


def event_message(iden: int, event: Any) -> Dict:
    """Return an event message."""
    return {"id": iden, "type": "event", "event": event}


@lru_cache(maxsize=128)
def cached_compressed_event_message(compressobj: Any, iden: int, event: Event) -> Any:
    """Return an event message.

    Serialize to json once per message.

    Since we can have many clients connected that are
    all getting many of the same events (mostly state changed)
    we can avoid serializing the same data for each connection.
    """
    message = compressobj.compress(
        message_to_json(event_message(iden, event)).encode("utf-8")
    )
    message = message + compressobj.flush(zlib.Z_SYNC_FLUSH)

    if message.endswith(DEFLATE_TAIL):
        return message[:-4]

    return message


def message_to_json(message: Any) -> str:
    """Serialize a websocket message to json."""
    try:
        return const.JSON_DUMP(message)
    except (ValueError, TypeError):
        _LOGGER.error(
            "Unable to serialize to JSON. Bad data found at %s",
            format_unserializable_data(
                find_paths_unserializable_data(message, dump=const.JSON_DUMP)
            ),
        )
        return const.JSON_DUMP(
            error_message(
                message["id"], const.ERR_UNKNOWN_ERROR, "Invalid JSON in response"
            )
        )
