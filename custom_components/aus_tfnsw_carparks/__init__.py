"""The TfNSW Car Park integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .api import TfNSWCarParkAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TfNSW Car Park from a config entry."""
    api_key = entry.data["api_key"]
    selected_carparks = entry.data.get("selected_carparks", [])
    
    api = TfNSWCarParkAPI(api_key)
    
    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            data = {}
            for carpark_id in selected_carparks:
                _LOGGER.debug("Fetching data for carpark %s", carpark_id)
                carpark_data = await api.get_carpark_data(carpark_id)
                if carpark_data:
                    _LOGGER.debug("Received data for carpark %s: %s", carpark_id, carpark_data)
                    data[carpark_id] = carpark_data
                else:
                    _LOGGER.warning("No data received for carpark %s", carpark_id)
            _LOGGER.debug("Total data collected: %s", data)
            return data
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}")
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="aus_tfnsw_carparks",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )
    
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
