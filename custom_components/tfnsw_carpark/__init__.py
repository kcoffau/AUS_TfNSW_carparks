
import logging
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
DOMAIN = "tfnsw_carpark"

async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    _LOGGER.debug("Entering async_setup_entry in __init__.py for TfNSW Carpark")

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
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
