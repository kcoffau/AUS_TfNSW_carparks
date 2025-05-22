import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

import aiohttp

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)

class TfNSWCarparkDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api_key: str, facility_ids: list):
        self.api_key = api_key
        self.facility_ids = facility_ids
        super().__init__(
            hass,
            _LOGGER,
            name="tfnsw_carpark",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        url = "https://api.transport.nsw.gov.au/v1/carpark/occupancy"
        headers = {"Authorization": f"apikey {self.api_key}"}
        params = {"facility_id": ",".join(map(str, self.facility_ids))} if self.facility_ids else {}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        _LOGGER.error(f"API request failed with status {response.status}")
                        raise UpdateFailed(f"API request failed with status {response.status}")
        except Exception as e:
            _LOGGER.error(f"Error fetching data: {e}")
            raise UpdateFailed(f"Error fetching data: {e}")

class TfNSWCarparkSensor(SensorEntity):
    def __init__(self, coordinator: TfNSWCarparkDataUpdateCoordinator, facility_id: int, facility_name: str):
        self.coordinator = coordinator
        self._facility_id = facility_id
        self._name = facility_name or f"Car Park {facility_id}"
        self._attr_unique_id = f"tfnsw_carpark_{facility_id}"
        self._attr_device_class = "measurement"
        self._attr_unit_of_measurement = "spots"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        if self.coordinator.data and "facilities" in self.coordinator.data:
            for facility in self.coordinator.data["facilities"]:
                if facility.get("facility_id") == self._facility_id:
                    occupancy = facility.get("occupancy", {})
                    total = occupancy.get("total", 0)
                    spots = facility.get("spots", 0)
                    return spots - total
        return None

    @property
    def extra_state_attributes(self):
        return {"facility_id": self._facility_id}

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.coordinator.async_remove_listener(self.async_write_ha_state)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    api_key = entry.data[CONF_API_KEY]
    car_parks = entry.options.get("car_parks", [])
    coordinator = TfNSWCarparkDataUpdateCoordinator(hass, api_key, car_parks)
    await coordinator.async_refresh()

    facility_names = {}
    if coordinator.data and "facilities" in coordinator.data:
        for facility in coordinator.data["facilities"]:
            facility_id = facility.get("facility_id")
            if facility_id in car_parks:
                facility_names[facility_id] = facility.get("facility_name", f"Car Park {facility_id}")

    entities = [
        TfNSWCarparkSensor(coordinator, facility_id, facility_names.get(facility_id, f"Car Park {facility_id}"))
        for facility_id in car_parks
    ]
    async_add_entities(entities)
