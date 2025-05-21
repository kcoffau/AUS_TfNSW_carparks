import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
import aiohttp

DOMAIN = "nsw_carpark"

class NswCarparkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            car_parks_str = user_input["car_parks"]
            try:
                car_parks_list = [int(id.strip()) for id in car_parks_str.split(",")]
            except ValueError:
                return self.async_show_form(
                    step_id="user",
                    errors={"base": "invalid_car_parks"},
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_API_KEY): str,
                            vol.Required("car_parks"): str,
                        }
                    ),
                )

            return self.async_create_entry(
                title="NSW Car Park",
                data={CONF_API_KEY: api_key},
                options={"car_parks": car_parks_list},
            )

        # Fetch car park list dynamically
        url = "https://api.transport.nsw.gov.au/v1/transport/carparks"  # Example endpoint, adjust as needed
        headers = {"Authorization": f"apikey {self.hass.data.get('api_key', '')}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        car_parks = data.get("facilities", [])
                        # Present car parks in UI (simplified, actual implementation may use multi-select)
                        return self.async_show_form(
                            step_id="user",
                            data_schema=vol.Schema(
                                {
                                    vol.Required(CONF_API_KEY): str,
                                    vol.Required("car_parks"): str,
                                }
                            ),
                        )
                    else:
                        return self.async_show_form(
                            step_id="user",
                            errors={"base": "api_error"},
                            data_schema=vol.Schema(
                                {
                                    vol.Required(CONF_API_KEY): str,
                                    vol.Required("car_parks"): str,
                                }
                            ),
                        )
        except Exception as e:
            return self.async_show_form(
                step_id="user",
                errors={"base": "connection_error"},
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_API_KEY): str,
                        vol.Required("car_parks"): str,
                    }
                ),
            )

    async def async_step_options(self, user_input=None):
        if user_input is not None:
            car_parks_str = user_input["car_parks"]
            try:
                car_parks_list = [int(id.strip()) for id in car_parks_str.split(",")]
            except ValueError:
                return self.async_show_form(
                    step_id="options",
                    errors={"base": "invalid_car_parks"},
                    data_schema=vol.Schema(
                        {
                            vol.Required("car_parks"): str,
                        }
                    ),
                )

            return self.async_create_entry(title="Options", data={"car_parks": car_parks_list})

        current_car_parks = self.config_entry.options.get("car_parks", [])
        current_car_parks_str = ",".join(map(str, current_car_parks))

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Required("car_parks", default=current_car_parks_str): str,
                }
            ),
        )
