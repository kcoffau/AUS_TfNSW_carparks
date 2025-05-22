import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector
import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)
DOMAIN = "tfnsw_carpark"

class TfNSWCarparkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_validate_api_key(self, api_key: str) -> bool:
        """Validate API key by fetching car park list."""
        url = "https://api.transport.nsw.gov.au/v1/carpark"
        headers = {"Authorization": f"apikey {api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    text = await response.text()
                    _LOGGER.debug(f"API response for validation: {text}")
                    if response.status == 200:
                        data = await response.json()
                        # Expecting a dictionary of facility_id: facility_name
                        if isinstance(data, dict) and data:
                            return True
                        else:
                            _LOGGER.error("Unexpected response format: not a dictionary or empty")
                            return False
                    elif response.status == 401:
                        _LOGGER.error("Authentication failed: Invalid API key")
                        return False
                    else:
                        _LOGGER.error(f"API request failed with status {response.status}: {text}")
                        return False
        except Exception as e:
            _LOGGER.error(f"Error validating API key: {e}")
            return False

    async def async_step_user(self, user_input=None):
        errors = {}
        car_parks_options = []
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            if not await self.async_validate_api_key(api_key):
                errors["base"] = "invalid_api_key"
            else:
                car_parks = user_input.get("car_parks", [])
                try:
                    car_parks_list = [int(facility_id) for facility_id in car_parks]
                    return self.async_create_entry(
                        title="TfNSW Car Park",
                        data={CONF_API_KEY: api_key},
                        options={"car_parks": car_parks_list},
                    )
                except ValueError:
                    errors["base"] = "invalid_car_parks"

        if user_input and CONF_API_KEY in user_input:
            url = "https://api.transport.nsw.gov.au/v1/carpark"
            headers = {"Authorization": f"apikey {user_input[CONF_API_KEY]}"}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            _LOGGER.debug(f"Car parks response: {data}")
                            # Transform dictionary to list of {value, label}
                            car_parks_options = [
                                {"value": str(facility_id), "label": facility_name}
                                for facility_id, facility_name in data.items()
                            ]
                        else:
                            errors["base"] = "api_error"
            except Exception as e:
                _LOGGER.error(f"Error fetching car parks: {e}")
                errors["base"] = "api_error"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Optional("car_parks"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=car_parks_options,
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"car_parks_hint": "Select car parks or leave blank to add later."},
        )

    async def async_step_options(self, user_input=None):
        errors = {}
        if user_input is not None:
            car_parks = user_input.get("car_parks", [])
            try:
                car_parks_list = [int(facility_id) for facility_id in car_parks]
                return self.async_create_entry(title="Options", data={"car_parks": car_parks_list})
            except ValueError:
                errors["base"] = "invalid_car_parks"

        current_car_parks = [str(facility_id) for facility_id in self.config_entry.options.get("car_parks", [])]
        car_parks_options = []
        api_key = self.config_entry.data[CONF_API_KEY]
        url = "https://api.transport.nsw.gov.au/v1/carpark"
        headers = {"Authorization": f"apikey {api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        _LOGGER.debug(f"Car parks response (options): {data}")
                        car_parks_options = [
                            {"value": str(facility_id), "label": facility_name}
                            for facility_id, facility_name in data.items()
                        ]
                    else:
                        errors["base"] = "api_error"
        except Exception as e:
            _LOGGER.error(f"Error fetching car parks: {e}")
            errors["base"] = "api_error"

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Optional("car_parks", default=current_car_parks): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=car_parks_options,
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"car_parks_hint": "Select car parks to monitor."},
        )
