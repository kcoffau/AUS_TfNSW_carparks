"""Config flow for TfNSW Car Park integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .api import TfNSWCarParkAPI
from .const import CONF_API_KEY, CONF_SELECTED_CARPARKS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TfNSW Car Park."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self._api_key: Optional[str] = None
        self._carpark_list: Dict[str, str] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            
            # Test the API key
            api = TfNSWCarParkAPI(api_key)
            try:
                if await api.test_connection():
                    self._api_key = api_key
                    # Get car park list for next step
                    self._carpark_list = await api.get_carpark_list()
                    await api.close()
                    return await self.async_step_carpark_selection()
                else:
                    errors["base"] = "auth"
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
            description_placeholders={
                "url": "https://opendata.transport.nsw.gov.au/"
            },
        )

    async def async_step_carpark_selection(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle car park selection step."""
        if user_input is not None:
            selected_carparks = user_input.get(CONF_SELECTED_CARPARKS, [])
            
            if not selected_carparks:
                return self.async_show_form(
                    step_id="carpark_selection",
                    data_schema=self._get_carpark_schema(),
                    errors={"base": "no_carparks_selected"},
                )
            
            return self.async_create_entry(
                title="TfNSW Car Park",
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_SELECTED_CARPARKS: selected_carparks,
                },
            )

        return self.async_show_form(
            step_id="carpark_selection",
            data_schema=self._get_carpark_schema(),
        )

    def _get_carpark_schema(self) -> vol.Schema:
        """Get schema for car park selection."""
        # Create options list with car park names, values are IDs
        options = [
            selector.SelectOptionDict(value=carpark_id, label=name)
            for carpark_id, name in self._carpark_list.items()
        ]
        
        return vol.Schema({
            vol.Required(CONF_SELECTED_CARPARKS): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for TfNSW Car Park."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._carpark_list: Dict[str, str] = {}

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            selected_carparks = user_input.get(CONF_SELECTED_CARPARKS, [])
            
            if not selected_carparks:
                errors["base"] = "no_carparks_selected"
            else:
                # Update the config entry
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        **self.config_entry.data,
                        CONF_SELECTED_CARPARKS: selected_carparks,
                    },
                )
                return self.async_create_entry(title="", data={})

        # Get fresh car park list
        api_key = self.config_entry.data[CONF_API_KEY]
        api = TfNSWCarParkAPI(api_key)
        
        try:
            self._carpark_list = await api.get_carpark_list()
        except Exception:
            errors["base"] = "cannot_connect"
        finally:
            await api.close()

        if errors:
            return self.async_show_form(
                step_id="init",
                errors=errors,
            )

        # Get currently selected car parks
        current_selection = self.config_entry.data.get(CONF_SELECTED_CARPARKS, [])

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(current_selection),
            errors=errors,
        )

    def _get_options_schema(self, current_selection: list) -> vol.Schema:
        """Get schema for options."""
        # Create options list with car park names, values are IDs
        options = [
            selector.SelectOptionDict(value=carpark_id, label=name)
            for carpark_id, name in self._carpark_list.items()
        ]
        
        return vol.Schema({
            vol.Required(
                CONF_SELECTED_CARPARKS,
                default=current_selection
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })
