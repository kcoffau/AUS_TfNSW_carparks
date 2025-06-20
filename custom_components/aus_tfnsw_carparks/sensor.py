"""Sensor platform for TfNSW Car Park integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TfNSW Car Park sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]
    
    # Get car park list to get names
    try:
        carpark_list = await api.get_carpark_list()
    except Exception as err:
        _LOGGER.error("Failed to get car park list for sensor setup: %s", err)
        return
    
    entities = []
    selected_carparks = config_entry.data.get("selected_carparks", [])
    
    for carpark_id in selected_carparks:
        if carpark_id in carpark_list:
            carpark_name = carpark_list[carpark_id]
            entities.extend([
                TfNSWCarParkSensor(
                    coordinator, carpark_id, carpark_name, "available_spots"
                ),
                TfNSWCarParkSensor(
                    coordinator, carpark_id, carpark_name, "total_spots"
                ),
                TfNSWCarParkSensor(
                    coordinator, carpark_id, carpark_name, "occupied_spots"
                ),
                TfNSWCarParkSensor(
                    coordinator, carpark_id, carpark_name, "occupancy_percentage"
                ),
            ])
    
    async_add_entities(entities)


class TfNSWCarParkSensor(CoordinatorEntity, SensorEntity):
    """Representation of a TfNSW Car Park sensor."""

    def __init__(
        self,
        coordinator,
        carpark_id: str,
        carpark_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._carpark_id = carpark_id
        self._carpark_name = carpark_name
        self._sensor_type = sensor_type
        
        # Set unique ID using carpark ID and sensor type
        self._attr_unique_id = f"{DOMAIN}_{carpark_id}_{sensor_type}"
        
        # Set entity ID using carpark ID for consistency
        self.entity_id = f"sensor.tfnsw_carpark_{carpark_id}_{sensor_type}"
        
        # Set friendly name using carpark name
        if sensor_type == "available_spots":
            self._attr_name = f"{carpark_name} Available Spots"
            self._attr_icon = "mdi:car"
            self._attr_native_unit_of_measurement = "spots"
        elif sensor_type == "total_spots":
            self._attr_name = f"{carpark_name} Total Spots"
            self._attr_icon = "mdi:car-multiple"
            self._attr_native_unit_of_measurement = "spots"
        elif sensor_type == "occupied_spots":
            self._attr_name = f"{carpark_name} Occupied Spots"
            self._attr_icon = "mdi:car-off"
            self._attr_native_unit_of_measurement = "spots"
        elif sensor_type == "occupancy_percentage":
            self._attr_name = f"{carpark_name} Occupancy"
            self._attr_icon = "mdi:percent"
            self._attr_native_unit_of_measurement = "%"
        
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data or self._carpark_id not in self.coordinator.data:
            _LOGGER.debug("No data available for carpark %s", self._carpark_id)
            return None
        
        data = self.coordinator.data[self._carpark_id]
        
        _LOGGER.debug("Processing %s for carpark %s", self._sensor_type, self._carpark_id)
        
        if self._sensor_type == "available_spots":
            # Available = Total capacity - Currently occupied
            total_capacity = data.get("spots")  # Total capacity
            occupied = data.get("occupancy", {}).get("total")  # Currently occupied
            
            _LOGGER.debug("Available spots calculation: capacity=%s, occupied=%s", total_capacity, occupied)
            
            if total_capacity is not None and occupied is not None:
                try:
                    capacity_int = int(total_capacity)
                    occupied_int = int(occupied)
                    available = capacity_int - occupied_int
                    _LOGGER.debug("Calculated available spots: %d", available)
                    return available
                except (ValueError, TypeError) as e:
                    _LOGGER.error("Error calculating available spots: %s", e)
                    return None
        
        elif self._sensor_type == "total_spots":
            # Total capacity from "spots" field
            total_capacity = data.get("spots")
            if total_capacity is not None:
                try:
                    return int(total_capacity)
                except (ValueError, TypeError) as e:
                    _LOGGER.error("Error parsing total spots: %s", e)
                    return None
        
        elif self._sensor_type == "occupied_spots":
            # Currently occupied spots from occupancy.total
            occupied = data.get("occupancy", {}).get("total")
            if occupied is not None:
                try:
                    return int(occupied)
                except (ValueError, TypeError) as e:
                    _LOGGER.error("Error parsing occupied spots: %s", e)
                    return None
        
        elif self._sensor_type == "occupancy_percentage":
            # Percentage occupied = (occupied / total_capacity) * 100
            total_capacity = data.get("spots")
            occupied = data.get("occupancy", {}).get("total")
            
            if total_capacity is not None and occupied is not None:
                try:
                    capacity_int = int(total_capacity)
                    occupied_int = int(occupied)
                    if capacity_int > 0:
                        percentage = round((occupied_int / capacity_int) * 100, 1)
                        return percentage
                    return 0
                except (ValueError, TypeError, ZeroDivisionError) as e:
                    _LOGGER.error("Error calculating occupancy percentage: %s", e)
                    return None
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data or self._carpark_id not in self.coordinator.data:
            return {}
        
        data = self.coordinator.data[self._carpark_id]
        location = data.get("location", {})
        occupancy = data.get("occupancy", {})
        
        attributes = {
            "carpark_id": self._carpark_id,
            "facility_name": data.get("facility_name"),
            "facility_id": data.get("facility_id"),
            "tfnsw_facility_id": data.get("tfnsw_facility_id"),
            "park_id": data.get("ParkID"),
            "suburb": location.get("suburb"),
            "address": location.get("address"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "last_updated": data.get("MessageDate"),
            "time": data.get("time"),
            "tsn": data.get("tsn"),
        }
        
        # Add capacity and occupancy details
        total_capacity = data.get("spots")
        occupied_spots = occupancy.get("total")
        
        if total_capacity is not None:
            try:
                attributes["total_capacity"] = int(total_capacity)
            except (ValueError, TypeError):
                attributes["total_capacity"] = total_capacity
        
        if occupied_spots is not None:
            try:
                attributes["occupied_spots"] = int(occupied_spots)
            except (ValueError, TypeError):
                attributes["occupied_spots"] = occupied_spots
        
        # Calculate available spots
        if total_capacity is not None and occupied_spots is not None:
            try:
                capacity = int(total_capacity)
                occupied = int(occupied_spots)
                attributes["available_spots"] = capacity - occupied
            except (ValueError, TypeError):
                pass
        
        # Add other occupancy details
        attributes.update({
            "monthlies": occupancy.get("monthlies"),
            "open_gate": occupancy.get("open_gate"),
            "transients": occupancy.get("transients"),
            "loop": occupancy.get("loop"),
        })
        
        # Add zone information if available
        zones = data.get("zones", [])
        if zones:
            zone_info = []
            for zone in zones:
                if zone.get("zone_name") and zone.get("zone_name").strip():
                    zone_data = {
                        "zone_id": zone.get("zone_id"),
                        "zone_name": zone.get("zone_name"),
                        "spots": zone.get("spots"),
                    }
                    zone_occupancy = zone.get("occupancy", {})
                    if zone_occupancy.get("transients"):
                        zone_data["transients"] = zone_occupancy.get("transients")
                    zone_info.append(zone_data)
            if zone_info:
                attributes["zones"] = zone_info
        
        return {k: v for k, v in attributes.items() if v is not None}

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data is not None 
            and self._carpark_id in self.coordinator.data
        )
