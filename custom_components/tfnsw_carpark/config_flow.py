
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector
import aiohttp
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
                async with session.get(url, headers=headers, params={"facility": "31"}, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    text = await response.text()
                    _LOGGER.debug(f"API response for facility=31: status={response.status}, body={text}")
                    if response.status == 200:
                        data = await response.json()
                        if data.get("facility_id"):
                            _LOGGER.debug("API key validation successful")
                            return True
                        else:
                            _LOGGER.error("Response does not contain facility_id, body: %s", text)
                            return False
                    elif response.status == 401:
                        _LOGGER.error("Authentication failed: Invalid API key, status=401")
                        return False
                    else:
                        _LOGGER.error(f"API request failed with status {response.status}, body: {text}")
                        return False
        except aiohttp.ClientConnectionError as e:
            _LOGGER.error(f"Connection error validating API key with facility=31: {e}")
            return False
        except Exception as e:
            _LOGGER.error(f"Unexpected error validating API key with facility=31: {e}", exc_info=True)
            return False

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Entering async_step_user in TfNSWCarparkConfigFlow")
        errors = {}
        existing_entry = await self.async_set_unique_id(DOMAIN, raise_on_progress=False)
        if existing_entry:
            _LOGGER.error("Config entry with unique_id '%s' already exists", DOMAIN)
            errors["base"] = "duplicate_entry"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_API_KEY): str,
                    }
                ),
                errors=errors,
                description_placeholders={
                    "message": "A config entry for Transport for NSW Carpark Availability already exists. Please remove the existing entry and try again."
                },
            )

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            if not await self.async_validate_api_key(api_key):
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
        url = "https://api.transport.nsw.gov.au/v1/carpark"
        headers = {"Authorization": f"apikey {api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    text = await response.text()
                    _LOGGER.debug(f"Car parks list response (options): status={response.status}, body={text}")
                    if response.status == 200:
                        data = await response.json()
                        car_parks = [
                            {"value": str(facility_id), "label": facility_name}
                            for facility_id, facility_name in data.items()
                            if str(facility_id).isdigit()
                        ]
                        _LOGGER.debug(f"Fetched car parks: {car_parks}")
                        return car_parks
                    else:
                        _LOGGER.warning(f"Failed to fetch car parks list: status={response.status}")
                        return None
        except Exception as e:
            _LOGGER.warning(f"Error fetching car parks: {e}")
            return None

    async def async_step_options(self, user_input=None):
        _LOGGER.debug("Entering async_step_options in TfNSWCarparkConfigFlow")
        errors = {}
        if user_input is not None:
            _LOGGER.debug(f"User input in async_step_options: {user_input}")
            car_parks = user_input.get("car_parks", [])
            try:
                car_parks_list = [int(facility_id) for facility_id in car_parks if facility_id and str(facility_id).isdigit()]
                options = self._initial_options.copy()
                if not car_parks_list:
                    _LOGGER.debug("No car parks selected, saving empty list")
                    options["car_parks"] = []
                else:
                    _LOGGER.debug(f"Saving car parks list: {car_parks_list}")
                    options["car_parks"] = car_parks_list
                _LOGGER.debug("Creating config entry with options: %s", options)
                await self.async_set_unique_id(DOMAIN)
                return self.async_create_entry(
                    title="Transport for NSW Carpark Availability",
                    data={CONF_API_KEY: self._api_key},
                    options=options,
                )
            except ValueError as e:
                _LOGGER.error(f"Error processing car parks selection: {e}")
                errors["base"] = "invalid_car_parks"
            except Exception as e:
                _LOGGER.error(f"Unexpected error saving car parks: {e}", exc_info=True)
                errors["base"] = "unknown_error"

        api_key = self._api_key
        _LOGGER.debug(f"Using API key for fetching car parks: {api_key[:5]}...")
        car_parks_options = await self.async_fetch_car_parks(api_key)
        if not car_parks_options:
            _LOGGER.debug("Using hardcoded fallback car parks list")
            car_parks_options = [
                {"value": "31", "label": "Park&Ride - Bella Vista"},
                {"value": "26", "label": "Park&Ride - Tallawong P1"},
                {"value": "29", "label": "Park&Ride - Kellyville (north)"},
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

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input=None):
        """Handle a flow initialized by the user."""
        _LOGGER.debug("Entering async_step_options in TfNSWCarparkOptionsFlowHandler")
        errors = {}
        if user_input is not None:
            _LOGGER.debug(f"User input in async_step_options: {user_input}")
            car_parks = user_input.get("car_parks", [])
            try:
                car_parks_list = [int(facility_id) for facility_id in car_parks if facility_id and str(facility_id).isdigit()]
                options = self.config_entry.options.copy()
                if not car_parks_list:
                    _LOGGER.debug("No car parks selected, saving empty list")
                    options["car_parks"] = []
                else:
                    _LOGGER.debug(f"Saving car parks list: {car_parks_list}")
                    options["car_parks"] = car_parks_list
                options["setup_complete"] = True

                # Update the config entry
                _LOGGER.debug("Before updating config entry: %s", self.config_entry.options)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options=options,
                )
                _LOGGER.debug("After updating config entry: %s", self.config_entry.options)

                # Attempt reload to ensure changes are applied
                entry_state = self.config_entry.state
                _LOGGER.debug("Config entry state before reload attempt: %s", entry_state)
                if entry_state in [config_entries.ConfigEntryState.LOADED, config_entries.ConfigEntryState.SETUP_ERROR]:
                    try:
                        _LOGGER.debug("Attempting to unload platforms before reload")
                        unload_result = await self.hass.config_entries.async_unload_platforms(self.config_entry, ["sensor"])
                        _LOGGER.debug("Unload platforms result: %s", unload_result)
                        if not unload_result:
                            _LOGGER.warning("Partial unload detected, forcing cleanup")
                        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                        _LOGGER.debug("Config entry reloaded successfully")
                    except Exception as e:
                        _LOGGER.error("Failed to reload config entry: %s", e, exc_info=True)
                        return self.async_show_form(
                            step_id="options",
                            data_schema=vol.Schema(
                                {
                                    vol.Optional("car_parks", default=[str(x) for x in car_parks_list]): selector.SelectSelector(
                                        selector.SelectSelectorConfig(
                                            options=await self.async_fetch_car_parks(self._api_key),
                                            multiple=True,
                                            mode=selector.SelectSelectorMode.DROPDOWN
                                        )
                                    ),
                                }
                            ),
                            errors={"base": "reload_failed"},
                            description_placeholders={"car_parks_hint": "Select car parks to monitor."},
                        )
                else:
                    _LOGGER.warning("Skipping reload due to invalid state: %s", entry_state)

                return self.async_create_entry(title="", data={})
            except ValueError as e:
                _LOGGER.error(f"Error processing car parks selection: %s", e)
                errors["base"] = "invalid_car_parks"
            except Exception as e:
                _LOGGER.error(f"Unexpected error saving car parks: %s", e, exc_info=True)
                errors["base"] = "unknown_error"

        car_parks_options = await self.async_fetch_car_parks(self._api_key)
        if not car_parks_options:
            _LOGGER.debug("Using hardcoded fallback car parks list")
            car_parks_options = [
                {"value": "31", "label": "Park&Ride - Bella Vista"},
                {"value": "26", "label": "Park&Ride - Tallawong P1"},
                {"value": "29", "label": "Park&Ride - Kellyville (north)"},
            ]

        current_car_parks = [str(car_park) for car_park in self.config_entry.options.get("car_parks", [])]
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

    async def async_fetch_car_parks(self, api_key: str):
        """Fetch the list of car parks from the API."""
        url = "https://api.transport.nsw.gov.au/v1/carpark"
        headers = {"Authorization": f"apikey {api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    text = await response.text()
                    _LOGGER.debug(f"Car parks list response (options): status={response.status}, body={text}")
                    if response.status == 200:
                        data = await response.json()
                        car_parks = [
                            {"value": str(facility_id), "label": facility_name}
                            for facility_id, facility_name in data.items()
                            if str(facility_id).isdigit()
                        ]
                        _LOGGER.debug(f"Fetched car parks: {car_parks}")
                        return car_parks
                    else:
                        _LOGGER.warning(f"Failed to fetch car parks list: status={response.status}")
                        return None
        except Exception as e:
            _LOGGER.warning(f"Error fetching car parks: %s", e)
            return None

    async def async_step_reauth(self, user_input=None):
        """Handle reauthorization if API key is invalid."""
        _LOGGER.debug("Entering async_step_reauth in TfNSWCarparkConfigFlow")
        self._api_key = None
        return await self.async_step_user(user_input)
