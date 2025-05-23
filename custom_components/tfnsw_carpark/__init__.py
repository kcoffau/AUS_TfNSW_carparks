
import logging
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
DOMAIN = "tfnsw_carpark"

async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up the TfNSW Carpark integration."""
    _LOGGER.debug("Entering async_setup_entry in __init__.py for TfNSW Carpark with entry_id: %s", entry.entry_id)

    # Check if API key exists
    api_key = entry.data.get("api_key")
    if not api_key:
        _LOGGER.error("API key not found in config entry data: %s", entry.data)
        return False

    # Always forward to sensor platform
    try:
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        _LOGGER.debug("Sensor setup initiated for car parks: %s", entry.options.get("car_parks", []))
        return True
    except Exception as e:
        _LOGGER.error("Failed to set up sensor platform: %s", e, exc_info=True)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading TfNSW Carpark config entry: %s", entry.entry_id)
    try:
        result = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
        _LOGGER.debug("Unload result: %s", result)
        return result
    except Exception as e:
        _LOGGER.error("Error unloading config entry: %s", e, exc_info=True)
        return False
