"""Support for Powerview scenes from a Powerview hub."""

import asyncio

from aiopvapi.helpers.aiorequest import PvApiConnectionError

DOMAIN = "hunterdouglas_powerview"


MANUFACTURER = "Hunter Douglas"

HUB_ADDRESS = "address"

SCENE_DATA = "sceneData"
SHADE_DATA = "shadeData"
ROOM_DATA = "roomData"
USER_DATA = "userData"

MAC_ADDRESS_IN_USERDATA = "macAddress"
SERIAL_NUMBER_IN_USERDATA = "serialNumber"
FIRMWARE_IN_USERDATA = "firmware"
MAINPROCESSOR_IN_USERDATA_FIRMWARE = "mainProcessor"
REVISION_IN_MAINPROCESSOR = "revision"
MODEL_IN_MAINPROCESSOR = "name"

FIRMWARE_IN_SHADE = "firmware"

FIRMWARE_REVISION = "revision"
FIRMWARE_SUB_REVISION = "subRevision"
FIRMWARE_BUILD = "build"

DEVICE_NAME = "device_name"
DEVICE_MAC_ADDRESS = "device_mac_address"
DEVICE_SERIAL_NUMBER = "device_serial_number"
DEVICE_REVISION = "device_revision"
DEVICE_INFO = "device_info"
DEVICE_MODEL = "device_model"
DEVICE_FIRMWARE = "device_firmware"

SCENE_NAME = "name"
SCENE_ID = "id"
ROOM_ID_IN_SCENE = "roomId"

SHADE_NAME = "name"
SHADE_ID = "id"
ROOM_ID_IN_SHADE = "roomId"

ROOM_NAME = "name"
ROOM_NAME_UNICODE = "name_unicode"
ROOM_ID = "id"

SHADE_RESPONSE = "shade"

STATE_ATTRIBUTE_ROOM_NAME = "roomName"

PV_API = "pv_api"
PV_HUB = "pv_hub"
PV_SHADES = "pv_shades"
PV_SCENE_DATA = "pv_scene_data"
PV_SHADE_DATA = "pv_shade_data"
PV_ROOM_DATA = "pv_room_data"
COORDINATOR = "coordinator"

HUB_EXCEPTIONS = (asyncio.TimeoutError, PvApiConnectionError)
