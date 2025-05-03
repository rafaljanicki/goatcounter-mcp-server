import httpx
import base64
import logging
from typing import Any, Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

class GoatcounterApiClientError(Exception):
    pass

class GoatcounterApiClient:
    def __init__(self, site_code: str, api_key: str, base_url_template: str = "https://{site_code}.goatcounter.com"):
        if not site_code:
            raise ValueError("site_code cannot be empty.")
        if not api_key:
            raise ValueError("api_key cannot be empty.")

        self.base_url = base_url_template.format(site_code=site_code)
        self.api_key = api_key
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        # Basic auth: username is "apitoken", password is the API key
        auth_bytes = f"apitoken:{self.api_key}".encode('utf-8')
        auth_header = base64.b64encode(auth_bytes).decode('utf-8')
        self.headers = {
            "Authorization": f"Basic {auth_header}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"/api/v0{endpoint}"
        try:
            response = await self.client.request(
                method,
                url,
                params=params,
                json=json_data,
                headers=self.headers
            )
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            if response.status_code == 204 or response.status_code == 202: # No content or Accepted
                return None
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            # Try to parse error details from Goatcounter response
            try:
                error_details = e.response.json()
                # Use Goatcounter's error format if available
                err_msg = error_details.get("error") or error_details.get("Error") or str(error_details.get("errors", {}))
                raise GoatcounterApiClientError(f"Goatcounter API Error ({e.response.status_code}): {err_msg}") from e
            except Exception: # If parsing fails or format is unexpected
                 raise GoatcounterApiClientError(f"Goatcounter API Error ({e.response.status_code}): {e.response.text}") from e
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise GoatcounterApiClientError(f"Request failed: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise GoatcounterApiClientError(f"An unexpected error occurred: {e}") from e

    async def get_me(self) -> Dict[str, Any]:
        """Get information about the current user and API key."""
        return await self._request("GET", "/me")

    async def list_sites(self) -> Dict[str, Any]:
        """List all sites accessible with the current API key."""
        return await self._request("GET", "/sites")

    async def list_paths(self, limit: int = 20, after: Optional[int] = None) -> Dict[str, Any]:
        """Get an overview of paths on this site (without statistics)."""
        params = {"Limit": limit}
        if after is not None:
            params["After"] = after
        return await self._request("GET", "/paths", params=params)

    async def get_stats_total(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, daily: bool = False) -> Dict[str, Any]:
        """Get total number of pageviews and visitors."""
        params: Dict[str, Any] = {"daily": daily}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        return await self._request("GET", "/stats/total", params=params)

    async def get_stats_hits(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None, daily: bool = False) -> Dict[str, Any]:
        """List pages."""
        params: Dict[str, Any] = {"limit": limit, "daily": daily}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/hits", params=params)

    async def get_stats_refs(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None, daily: bool = False) -> Dict[str, Any]:
        """List referrers."""
        params: Dict[str, Any] = {"limit": limit, "daily": daily}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/refs", params=params)

    async def get_stats_browsers(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None, daily: bool = False) -> Dict[str, Any]:
        """List browsers."""
        params: Dict[str, Any] = {"limit": limit, "daily": daily}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/browsers", params=params)

    async def get_stats_systems(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None, daily: bool = False) -> Dict[str, Any]:
        """List operating systems."""
        params: Dict[str, Any] = {"limit": limit, "daily": daily}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/systems", params=params)

    async def get_stats_sizes(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None, daily: bool = False) -> Dict[str, Any]:
        """List screen sizes."""
        params: Dict[str, Any] = {"limit": limit, "daily": daily}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/sizes", params=params)

    async def get_stats_locations(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None, daily: bool = False) -> Dict[str, Any]:
        """List locations."""
        params: Dict[str, Any] = {"limit": limit, "daily": daily}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/locations", params=params)

    # Add more methods here for other endpoints like /count, /export, etc. as needed

    async def close(self):
        await self.client.aclose() 