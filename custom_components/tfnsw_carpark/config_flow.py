
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
                        _LOGGER.error(f"API request failed with status {response.status}, body: %s", text)
                        return False
        except aiohttp.ClientConnectionError as e:
            _LOGGER.error(f"Connection error validating API key with facility=31: %s", e)
            return False
        except Exception as e:
            _LOGGER.error(f"Unexpected error validating API key with facility=31: %s", e, exc_info=True)
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
        url = "https://api.transport.nsw.gov.au/v1/carpark/list"
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

    async def async_step_options(self, user_input=None):
        _LOGGER.debug("Entering async_step_options in TfNSWCarparkConfigFlow")
        errors = {}
        if user_input is not None:
            _LOGGER.debug(f"User input in async_step_options: %s", user_input)
            car_parks = user_input.get("car_parks", [])
            try:
                car_parks_list = [int(facility_id) for facility_id in car_parks if facility_id and str(facility_id).isdigit()]
                options = self._initial_options.copy()
                if not car_parks_list:
                    _LOGGER.debug("No car parks selected, saving empty list")
                    options["car_parks"] = []
                else:
                    _LOGGER.debug(f"Saving car parks list: %s", car_parks_list)
                    options["car_parks"] = car_parks_list
                options["setup_complete"] = True
                _LOGGER.debug("Creating config entry with options: %s", options)
                await self.async_set_unique
