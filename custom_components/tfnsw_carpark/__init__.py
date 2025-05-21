import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, core

DOMAIN = "nsw_carpark"

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({}, extra=vol.ALLOW_EXTRA)}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: core.HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry):
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True

async def async_unload_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry):
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return unload_ok
