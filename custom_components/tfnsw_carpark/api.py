"""API client for TfNSW Car Park."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp
import async_timeout

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class TfNSWCarParkAPI:
    """TfNSW Car Park API client."""

    def __init__(self, api_key: str) -> None:
        """Initialize the API client."""
        self.api_key = api_key
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get aiohttp session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self) -> None:
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(self, url: str) -> Dict[str, Any]:
        """Make a request to the API."""
        headers = {
            "accept": "application/json",
            "Authorization": f"apikey {self.api_key}"
        }
        
        session = await self._get_session()
        
        try:
            async with async_timeout.timeout(10):
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    return await response.json()
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout occurred while connecting to TfNSW API")
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("Error occurred while connecting to TfNSW API: %s", err)
            raise

    async def get_carpark_list(self) -> Dict[str, str]:
        """Get list of available car parks."""
        try:
            data = await self._request(API_BASE_URL)
            _LOGGER.debug("Retrieved %d car parks", len(data))
            return data
        except Exception as err:
            _LOGGER.error("Failed to get car park list: %s", err)
            raise

    async def get_carpark_data(self, facility_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific car park."""
        url = f"{API_BASE_URL}?facility={facility_id}"
        
        try:
            data = await self._request(url)
            _LOGGER.debug("Retrieved data for car park %s", facility_id)
            return data
        except Exception as err:
            _LOGGER.error("Failed to get data for car park %s: %s", facility_id, err)
            return None

    async def test_connection(self) -> bool:
        """Test the API connection."""
        try:
            await self.get_carpark_list()
            return True
        except Exception:
            return False
