import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector
import aiohttp
import async_timeout
import logging

_LOGGER = logging.getLogger(__name__)
DOMAIN = "tfnsw_carpark"

class TfNSWCarparkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        self._api_key = None
        self._initial_options = {"car_parks": [], "setup_complete": False}
        self._car_parks = []

    async def async_validate_api_key(self, api_key: str) -> bool:
        """Validate API key by fetching a known facility."""
        url = "https://api.transport.nsw.gov.au/v1/carpark"
        headers = {"Authorization": f"apikey {api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                _LOGGER.debug(f"Attempting to validate API key {api_key[:5]}... with facility=31")
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=headers, params={"facility": "31"}) as response:
                        text = await response.text()
                        _LOGGER.debug(f"API response for facility=31: status={response.status}, body={text}")
                        if response.status == 200:
                            try:
                                data = await response.json()
                                if data.get("facility_id") or data.get("occupancy"):
                                    _LOGGER.debug("API key validation successful")
                                    return True
                                else:
                                    _LOGGER.error("Response does not contain expected data, body: %s", text)
                                    return False
                            except Exception as json_err:
                                _LOGGER.error("Failed to parse JSON response: %s", json_err)
                                return False
                        elif response.status == 401:
                            _LOGGER.error("Authentication failed: Invalid API key, status=401")
                            return False
                        else:
                            _LOGGER.error(f"API request failed with status {response.status}, body: %s", text)
                            return False
        except aiohttp.ClientConnectionError as e:
            _LOGGER.error(f"Connection error validating API key: %s", e)
            return False
        except Exception as e:
            _LOGGER.error(f"Unexpected error validating API key: %s", e, exc_info=True)
            return False

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        _LOGGER.debug("Entering async_step_user in TfNSWCarparkConfigFlow")
        errors = {}
        
        # Check for existing entry
        existing_entry = await self.async_set_unique_id(DOMAIN, raise_on_progress=False)
        if existing_entry:
            _LOGGER.error("Config entry with unique_id '%s' already exists", DOMAIN)
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            if not api_key:
                errors["base"] = "missing_api_key"
            elif not await self.async_validate_api_key(api_key):
                errors["base"] = "invalid_api_key"
            else:
                _LOGGER.debug("API key validated, storing for options step")
                self._api_key = api_key
                _LOGGER.debug("Proceeding to options flow for car park selection")
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={"message": "Enter your Transport for NSW API key."},
        )

    async def async_fetch_car_parks(self, api_key: str):
        """Fetch the list of car parks from the API."""
        # Note: You'll need to find the correct endpoint for getting the facilities list
        # This is a placeholder - check TfNSW API documentation
        url = "https://api.transport.nsw.gov.au/v1/carpark/facilities"
        headers = {"Authorization": f"apikey {api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(15):
                    async with session.get(url, headers=headers) as response:
                        text = await response.text()
                        _LOGGER.debug(f"Car parks list response: status={response.status}, body={text}")
                        if response.status == 200:
                            try:
                                data = await response.json()
                                # Adjust this based on actual API response structure
                                if isinstance(data, dict):
                                    car_parks = [
                                        {"value": str(facility_id), "label": facility_name}
                                        for facility_id, facility_name in data.items()
                                        if str(facility_id).isdigit()
                                    ]
                                elif isinstance(data, list):
                                    car_parks = [
                                        {"value": str(item.get("id", "")), "label": item.get("name", f"Car Park {item.get('id', '')}")}
                                        for item in data
                                        if item.get("id")
                                    ]
                                else:
                                    _LOGGER.warning("Unexpected API response format")
                                    return None
                                
                                _LOGGER.debug(f"Fetched car parks: {car_parks}")
                                return car_parks
                            except Exception as json_err:
                                _LOGGER.error(f"Failed to parse car parks JSON: {json_err}")
                                return None
                        else:
                            _LOGGER.warning(f"Failed to fetch car parks list: status={response.status}, body={text}")
                            return None
        except Exception as e:
            _LOGGER.warning(f"Error fetching car parks: %s", e)
            return None

    async def async_step_options(self, user_input=None):
        """Handle the car park selection step."""
        _LOGGER.debug("Entering async_step_options in TfNSWCarparkConfigFlow")
        errors = {}
        
        if user_input is not None:
            _LOGGER.debug(f"User input in async_step_options: %s", user_input)
            car_parks = user_input.get("car_parks", [])
            try:
                car_parks_list = []
                for facility_id in car_parks:
                    if facility_id and str(facility_id).strip():
                        # Handle both string and int IDs
                        clean_id = str(facility_id).strip()
                        if clean_id.isdigit():
                            car_parks_list.append(int(clean_id))
                        else:
                            car_parks_list.append(clean_id)
                
                options = self._initial_options.copy()
                options["car_parks"] = car_parks_list
                options["setup_complete"] = True
                
                _LOGGER.debug("Creating config entry with options: %s", options)
                await self.async_set_unique_id(DOMAIN)
                return self.async_create_entry(
                    title="Transport for NSW Carpark Availability",
                    data={CONF_API_KEY: self._api_key},
                    options=options,
                )
            except ValueError as e:
                _LOGGER.error(f"Error processing car parks selection: %s", e)
                errors["base"] = "invalid_car_parks"
            except Exception as e:
                _LOGGER.error(f"Unexpected error saving car parks: %s", e, exc_info=True)
                errors["base"] = "unknown_error"

        # Fetch available car parks
        api_key = self._api_key
        _LOGGER.debug(f"Using API key for fetching car parks: {api_key[:5]}...")
        car_parks_options = await self.async_fetch_car_parks(api_key)
        
        if not car_parks_options:
            _LOGGER.debug("Using hardcoded fallback car parks list")
            car_parks_options = [
                {"value": "31", "label": "Park&Ride - Bella Vista"},
                {"value": "26", "label": "Park&Ride - Tallawong P1"},
                {"value": "29", "label": "Park&Ride - Kellyville (north)"},
                {"value": "32", "label": "Park&Ride - Rouse Hill"},
                {"value": "33", "label": "Park&Ride - Castle Hill"},
            ]

        current_car_parks = [str(car_park) for car_park in self._car_parks]
        _LOGGER.debug(f"Current car parks: {current_car_parks}")

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

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TfNSWCarparkOptionsFlowHandler(config_entry)


class TfNSWCarparkOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle options flow for TfNSW Carpark."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__(config_entry)
        self._api_key = self.config_entry.data.get(CONF_API_KEY)

    async def async_fetch_car_parks(self, api_key: str):
        """Fetch the list of car parks from the API."""
        url = "https://api.transport.nsw.gov.au/v1/carpark/facilities"
        headers = {"Authorization": f"apikey {api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(15):
                    async with session.get(url, headers=headers) as response:
                        text = await response.text()
                        _LOGGER.debug(f"Car parks list response (options): status={response.status}, body={text}")
                        if response.status == 200:
                            try:
                                data = await response.json()
                                # Adjust this based on actual API response structure
                                if isinstance(data, dict):
                                    car_parks = [
                                        {"value": str(facility_id), "label": facility_name}
                                        for facility_id, facility_name in data.items()
                                        if str(facility_id).isdigit()
                                    ]
                                elif isinstance(data, list):
                                    car_parks = [
                                        {"value": str(item.get("id", "")), "label": item.get("name", f"Car Park {item.get('id', '')}")}
                                        for item in data
                                        if item.get("id")
                                    ]
                                else:
                                    _LOGGER.warning("Unexpected API response format in options flow")
                                    return None
                                
                                _LOGGER.debug(f"Fetched car parks for options: {car_parks}")
                                return car_parks
                            except Exception as json_err:
                                _LOGGER.error(f"Failed to parse car parks JSON in options: {json_err}")
                                return None
                        else:
                            _LOGGER.warning(f"Failed to fetch car parks list in options: status={response.status}")
                            return None
        except Exception as e:
            _LOGGER.warning(f"Error fetching car parks in options: %s", e)
            return None

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input=None):
        """Handle a flow initialized by the user."""
        _LOGGER.debug("Entering async_step_options in TfNSWCarparkOptionsFlowHandler")
        errors = {}
        
        if user_input is not None:
            _LOGGER.debug(f"User input in options flow: {user_input}")
            car_parks = user_input.get("car_parks", [])
            try:
                car_parks_list = []
                for facility_id in car_parks:
                    if facility_id and str(facility_id).strip():
                        clean_id = str(facility_id).strip()
                        if clean_id.isdigit():
                            car_parks_list.append(int(clean_id))
                        else:
                            car_parks_list.append(clean_id)
                
                options = self.options.copy()
                options["car_parks"] = car_parks_list
                options["setup_complete"] = True

                _LOGGER.debug("Updating config entry options: %s", options)
                return self.async_create_entry(title="", data=options)
                
            except ValueError as e:
                _LOGGER.error(f"Error processing car parks selection in options: %s", e)
                errors["base"] = "invalid_car_parks"
            except Exception as e:
                _LOGGER.error(f"Unexpected error saving car parks in options: %s", e, exc_info=True)
                errors["base"] = "unknown_error"

        # Fetch available car parks
        car_parks_options = await self.async_fetch_car_parks(self._api_key)
        if not car_parks_options:
            _LOGGER.debug("Using hardcoded fallback car parks list in options")
            car_parks_options = [
                {"value": "31", "label": "Park&Ride - Bella Vista"},
                {"value": "26", "label": "Park&Ride - Tallawong P1"},
                {"value": "29", "label": "Park&Ride - Kellyville (north)"},
                {"value": "32", "label": "Park&Ride - Rouse Hill"},
                {"value": "33", "label": "Park&Ride - Castle Hill"},
            ]

        current_car_parks = [str(car_park) for car_park in self.options.get("car_parks", [])]
        _LOGGER.debug(f"Current car parks in options: {current_car_parks}")

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
