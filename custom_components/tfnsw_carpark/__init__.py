
import logging
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
DOMAIN = "tfnsw_carpark"

async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up the TfNSW Carpark integration."""
    _LOGGER.debug("Entering async_setup_entry in __init__.py for TfNSW Carpark")

    # Check if API key exists
    api_key = entry.data.get("api_key")
    if not api_key:
        _LOGGER.error("API key not found in config entry data: %s", entry.data)
        return False

    # Check if setup is complete
    setup_complete = entry.options.get("setup_complete", False)
    if not setup_complete:
        _LOGGER.debug("Setup not complete, triggering options flow")
        hass.async_create_task(
            hass.config_entries.options.async_init(entry.entry_id)
        )
        return True

    # Proceed with setup if car parks are selected
    car_parks = entry.options.get("car_parks", [])
    _LOGGER.debug(f"Setting up sensors with car parks: {car_parks}")
    if not car_parks:
        _LOGGER.warning("No car parks selected in options, no sensors will be created")
        return True

    # Forward the setup to the sensor platform
    try:
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        _LOGGER.debug("Sensor setup initiated for car parks: %s", car_parks)
        return True
    except Exception as e:
        _LOGGER.error("Failed to set up sensor platform: %s", e, exc_info=True)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading TfNSW Carpark config entry")
    try:
        # Unload the sensor platform
        result = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
        if not result:
            _LOGGER.warning("Partial unload of platforms, forcing cleanup")
        _LOGGER.debug("Unload result: %s", result)
        return result
    except Exception as e:
        _LOGGER.error("Error unloading config entry: %s", e, exc_info=True)
        return False
