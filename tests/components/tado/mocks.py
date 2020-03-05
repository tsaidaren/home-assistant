"""Mocks for the tado component."""
import json
import os

from tado.tado_device import TadoZoneData

from tests.common import load_fixture


async def _mock_tado_climate_zone_from_fixture(hass, file):
    return TadoZoneData(_load_json_fixture(hass, file))


async def _load_json_fixture(hass, path):
    fixture = await hass.async_add_executor_job(
        load_fixture, os.path.join("tado", path)
    )
    return json.loads(fixture)
