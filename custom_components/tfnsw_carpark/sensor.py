import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady
import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)
DOMAIN = "tfnsw_carpark"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    """Set up the sensor platform."""
    _LOGGER.debug("Starting setup for TfNSW Carpark with entry_id: %s, data: %s, options: %s", entry.entry_id, entry.data, entry.options)

    # Check if setup is complete
    setup_complete = entry.options.get("setup_complete", False)
    if not setup_complete:
        _LOGGER.debug("Setup not complete, skipping entity creation")
        return True

    # Retrieve API key and car parks
    api_key = entry.data.get("api_key")
    if not api_key:
        _LOGGER.error("API key missing in config entry data: %s", entry.data)
        return False

    car_parks = entry.options.get("car_parks", [])
    if not car_parks:
        _LOGGER.warning("No car parks configured in options: %s, skipping setup", entry.options)
        return True

    _LOGGER.debug("Configuring coordinator for car parks: %s", car_parks)

    # Create a data coordinator for fetching car park data
    async def async_update_data():
        """Fetch data from the TfNSW API for all configured car parks."""
        data = {}
        headers = {"Authorization": f"apikey {api_key}"}
        url = "https://api.transport.nsw.gov.au/v1/carpark"
        _LOGGER.debug("Initiating API data fetch for car parks: %s", car_parks)
        try:
            async with aiohttp.ClientSession() as session:
                for car_park_id in car_parks:
                    params = {"facility": str(car_park_id)}
                    async with async_timeout.timeout(10):
                        async with session.get(url, headers=headers, params=params) as response:
                            response_text = await response.text()
                            _LOGGER.debug("API response for car park %s: status=%d, body=%s", car_park_id, response.status, response_text)
                            if response.status == 200:
                                result = await response.json()
                                data[car_park_id] = result.get("occupancy", {}).get("total", "Unknown")
                            else:
                                _LOGGER.error("API fetch failed for car park %s: status=%d, body=%s", car_park_id, response.status, response_text)
                                data[car_park_id] = "Error"
        except Exception as e:
            _LOGGER.error("Exception during API fetch for car parks: %s", e, exc_info=True)
            raise ConfigEntryNotReady(f"Failed to fetch data for car parks: {e}")
        _LOGGER.debug("Update data completed with result: %s", data)
        return data

    # Set up the coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="TfNSW Carpark Coordinator",
        update_method=async_update_data,
        update_interval=300,  # Update every 5 minutes
    )

    # Perform an initial refresh with detailed logging
    _LOGGER.debug("Attempting initial refresh for coordinator with entry: %s", entry.entry_id)
    try:
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("Coordinator initial refresh succeeded")
    except ConfigEntryNotReady as e:
        _LOGGER.error("Coordinator initial refresh failed: %s", e, exc_info=True)
        raise
    except Exception as e:
        _LOGGER.error("Unexpected error during initial coordinator refresh: %s", e, exc_info=True)
        return False

    # Create sensor entities for each car park
    entities = []
    _LOGGER.debug("Creating sensors for car parks: %s", car_parks)
    for car_park_id in car_parks:
        entities.append(TfNSWCarparkSensor(coordinator, entry, car_park_id))

    async_add_entities(entities)
    _LOGGER.debug("Sensors successfully added for car parks: %s", car_parks)

    # Store the coordinator in hass.data for unload purposes
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("Coordinator stored for entry_id: %s", entry.entry_id)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the sensor platform."""
    _LOGGER.debug("Unloading sensor platform for TfNSW Carpark entry: %s", entry.entry_id)
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        if coordinator._unsub_refresh is not None:
            coordinator._unsub_refresh()
            coordinator._unsub_refresh = None
            _LOGGER.debug("Coordinator unsubscribed for entry: %s", entry.entry_id)
    return True

class TfNSWCarparkSensor(CoordinatorEntity, SensorEntity):
    """Representation of a TfNSW Carpark sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry, car_park_id: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._car_park_id = car_park_id
        self._attr_name = f"Park&Ride {car_park_id}"
        self._attr_unique_id = f"tfnsw_carpark_{car_park_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"tfnsw_carpark_{car_park_id}")},
            "name": f"Car Park {car_park_id}",
            "manufacturer": "Transport for NSW",
        }
        self._attr_state_class = "measurement"
        self._attr_unit_of_measurement = "spaces"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._car_park_id, "Unknown")

    @property
    def available(self):
        """Return if the sensor is available."""
        return self.coordinator.data.get(self._car_park_id) is not None
