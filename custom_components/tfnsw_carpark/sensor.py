
import asyncio
import logging
from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)
DOMAIN = "tfnsw_carpark"

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    api_key = entry.data[CONF_API_KEY]
    car_parks = entry.options.get("car_parks", [])

    _LOGGER.debug(f"Setting up sensors with car parks: {car_parks}")

    if not car_parks:
        _LOGGER.warning("No car parks selected in options, no sensors will be created")
        return

    coordinator = TfNSWCarparkCoordinator(hass, api_key)
    await coordinator.async_config_entry_first_refresh()

    sensors = [TfNSWCarparkSensor(coordinator, park_id) for park_id in car_parks]
    async_add_entities(sensors)

class TfNSWCarparkCoordinator(DataUpdateCoordinator):
    """Data update coordinator for TfNSW car park data."""

    def __init__(self, hass, api_key):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.api_key = api_key

    async def _async_update_data(self):
        """Fetch data from the TfNSW API."""
        url = "https://api.transport.nsw.gov.au/v1/carpark"
        headers = {"Authorization": f"apikey {self.api_key}"}
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            raise UpdateFailed(f"API request failed with status {response.status}")
                        data = await response.json()
                        return data
        except Exception as e:
            raise UpdateFailed(f"Error fetching car park data: {e}")

class TfNSWCarparkSensor(SensorEntity):
    """Representation of a TfNSW car park sensor."""

    def __init__(self, coordinator, park_id):
        self.coordinator = coordinator
        self._park_id = park_id
        self._attr_unique_id = f"tfnsw_carpark_{park_id}"
        self._attr_name = f"Park&Ride {park_id}"
        self._attr_icon = "mdi:car-parking-lights"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        park_data = self.coordinator.data.get(str(self._park_id))
        return park_data.get("occupancy", {}).get("total") if park_data else None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        park_data = self.coordinator.data.get(str(self._park_id))
        if park_data:
            return {
                "facility_id": self._park_id,
                "facility_name": park_data.get("facility_name"),
                "spots": park_data.get("spots"),
                "loop": park_data.get("occupancy", {}).get("loop"),
                "monthlies": park_data.get("occupancy", {}).get("monthlies"),
                "transients": park_data.get("occupancy", {}).get("transients"),
                "last_updated": park_data.get("MessageDate"),
            }
        return {}

    async def async_update(self):
        """Update the sensor state."""
        await self.coordinator.async_request_refresh()
