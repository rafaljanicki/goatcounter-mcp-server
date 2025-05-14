import httpx
import os
import logging
import asyncio # Added for sleep
import random  # Added for jitter
from typing import Optional, Annotated, Dict, Any

from pydantic import BaseModel, Field
from dotenv import load_dotenv

from fastmcp import FastMCP

# --- Configuration & Setup ---
load_dotenv() # Load environment variables from .env file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

goatcounter_code = os.getenv("GOATCOUNTER_CODE")
goatcounter_api_key = os.getenv("GOATCOUNTER_API_KEY")

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
        # Use Bearer token authentication as per primary documentation
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
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
        """
        Get an overview of paths on this site (without statistics).
        
        Parameters:
            limit (int, optional): Limit number of returned results (1-200, default 20).
            after (int, optional): Only select paths after this ID, for pagination.
        """
        params = {"Limit": limit}
        if after is not None:
            params["After"] = after
        return await self._request("GET", "/paths", params=params)

    async def get_stats_total(self, start: Optional[str] = None, end: Optional[str] = None, include_paths: Optional[list[int]] = None) -> Dict[str, Any]:
        """
        Get total number of pageviews and visitors.

        Parameters:
            start (str, optional): Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            end (str, optional): End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            include_paths (list[int], optional): Filter by specific path IDs.
        """
        params: Dict[str, Any] = {}
        if start: params["start"] = start
        if end: params["end"] = end
        if include_paths: params["include_paths"] = include_paths
        return await self._request("GET", "/stats/total", params=params)

    async def get_stats_hits(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None, daily: bool = False) -> Dict[str, Any]:
        """
        List page statistics (pageviews and visitors per path).

        Parameters:
            start (str, optional): Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            end (str, optional): End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            filter (str, optional): Filter results (exact meaning depends on endpoint).
            limit (int, optional): Limit number of returned results (1-100, default 20).
            after (int, optional): Pagination cursor.
            daily (bool, optional): Group results by day instead of for the entire period.
        """
        params: Dict[str, Any] = {"limit": limit, "daily": daily}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/hits", params=params)

    async def get_stats_refs(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None) -> Dict[str, Any]:
        """
        List referrer statistics.

        Parameters:
            start (str, optional): Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            end (str, optional): End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            filter (str, optional): Filter results (exact meaning depends on endpoint).
            limit (int, optional): Limit number of returned results (1-100, default 20).
            after (int, optional): Pagination cursor.
        """
        params: Dict[str, Any] = {"limit": limit}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/toprefs", params=params)

    async def get_stats_browsers(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None) -> Dict[str, Any]:
        """
        List browser statistics.

        Parameters:
            start (str, optional): Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            end (str, optional): End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            filter (str, optional): Filter results (exact meaning depends on endpoint).
            limit (int, optional): Limit number of returned results (1-100, default 20).
            after (int, optional): Pagination cursor.
        """
        params: Dict[str, Any] = {"limit": limit}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/browsers", params=params)

    async def get_stats_systems(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None) -> Dict[str, Any]:
        """
        List operating system statistics.

        Parameters:
            start (str, optional): Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            end (str, optional): End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            filter (str, optional): Filter results (exact meaning depends on endpoint).
            limit (int, optional): Limit number of returned results (1-100, default 20).
            after (int, optional): Pagination cursor.
        """
        params: Dict[str, Any] = {"limit": limit}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/systems", params=params)

    async def get_stats_sizes(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None) -> Dict[str, Any]:
        """
        List screen size statistics.

        Parameters:
            start (str, optional): Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            end (str, optional): End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            filter (str, optional): Filter results (exact meaning depends on endpoint).
            limit (int, optional): Limit number of returned results (1-100, default 20).
            after (int, optional): Pagination cursor.
        """
        params: Dict[str, Any] = {"limit": limit}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/sizes", params=params)

    async def get_stats_locations(self, start: Optional[str] = None, end: Optional[str] = None, filter: Optional[str] = None, limit: int = 20, after: Optional[int] = None) -> Dict[str, Any]:
        """
        List location statistics.

        Parameters:
            start (str, optional): Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            end (str, optional): End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).
            filter (str, optional): Filter results (exact meaning depends on endpoint).
            limit (int, optional): Limit number of returned results (1-100, default 20).
            after (int, optional): Pagination cursor.
        """
        params: Dict[str, Any] = {"limit": limit}
        if start: params["start"] = start
        if end: params["end"] = end
        if filter: params["filter"] = filter
        if after is not None: params["after"] = after
        return await self._request("GET", "/stats/locations", params=params)

    # Add more methods here for other endpoints like /count, /export, etc. as needed

    async def close(self):
        await self.client.aclose() 

# Global variable to hold the client instance (lazy initialization)
_api_client_instance: Optional[GoatcounterApiClient] = None

def get_api_client() -> GoatcounterApiClient:
    """Gets or initializes the GoatcounterApiClient instance."""
    global _api_client_instance
    if _api_client_instance is None:
        logger.info("Initializing GoatcounterApiClient...")
        # Check for credentials only when the client is first needed
        if not goatcounter_code:
            raise ValueError("GOATCOUNTER_CODE environment variable not set.")
        if not goatcounter_api_key:
            raise ValueError("GOATCOUNTER_API_KEY environment variable not set.")
        _api_client_instance = GoatcounterApiClient(
            site_code=goatcounter_code,
            api_key=goatcounter_api_key
        )
        logger.info("GoatcounterApiClient initialized.")
    return _api_client_instance

# --- FastMCP Instance ---
mcp = FastMCP(
    name="GoatcounterMCP",
    description="MCP server for interacting with the Goatcounter API.",
    prefix="Goatcounter"
)

# --- Constants for Backoff ---
MAX_RETRIES = 5
BASE_BACKOFF_DELAY = 1.0 # seconds

# --- Helper Function for Error Handling ---
async def _call_api(api_method, **kwargs):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            result = await api_method(**kwargs)
            # Ensure None is returned correctly if API gives 202/204
            return result if result is not None else {}
        except GoatcounterApiClientError as e:
            # Check for rate limit status code (assuming client provides it)
            # 429 is the standard HTTP status code for Too Many Requests
            is_rate_limit = getattr(e, 'status_code', None) == 429

            if is_rate_limit:
                retries += 1
                if retries >= MAX_RETRIES:
                    logger.error(f"Rate limited. Max retries ({MAX_RETRIES}) exceeded.")
                    raise Exception(f"Goatcounter API rate limit exceeded after {MAX_RETRIES} retries: {e}") from e

                wait_time = None
                # Try to get wait time from X-Rate-Limit-Reset header
                headers = getattr(e, 'headers', {})
                reset_header = headers.get('X-Rate-Limit-Reset')
                if reset_header:
                    try:
                        wait_time = float(reset_header) + 1.0 # Add a 1s buffer
                        logger.warning(f"Rate limited. Retrying after {wait_time:.2f} seconds (from header). Attempt {retries}/{MAX_RETRIES}.")
                    except (ValueError, TypeError):
                        logger.warning("Could not parse X-Rate-Limit-Reset header: {reset_header}")
                        wait_time = None # Fallback to exponential backoff

                # If header not present or invalid, use exponential backoff
                if wait_time is None:
                    backoff_delay = BASE_BACKOFF_DELAY * (2 ** (retries - 1))
                    jitter = random.uniform(0, 0.5) # Add jitter
                    wait_time = backoff_delay + jitter
                    logger.warning(f"Rate limited. Retrying after {wait_time:.2f} seconds (exponential backoff). Attempt {retries}/{MAX_RETRIES}.")

                await asyncio.sleep(wait_time)
                continue # Retry the API call
            else:
                # Handle other API client errors
                logger.error(f"Goatcounter API Client Error: {e}")
                raise Exception(f"Goatcounter API Error: {e}") from e
        except Exception as e:
            # Handle unexpected errors
            logger.exception(f"Unexpected error calling Goatcounter API: {e}")
            raise Exception(f"An unexpected internal server error occurred: {e}")

    # Should not be reached if MAX_RETRIES > 0, but added for safety
    raise Exception("API call failed after exhausting retries.")

# --- MCP Tool Definitions ---

@mcp.tool(name="get_me", description="Get information about the current Goatcounter user and API key.")
async def get_me():
    client = get_api_client()
    return await _call_api(client.get_me)

@mcp.tool(name="list_sites", description="List all Goatcounter sites accessible with the current API key.")
async def list_sites():
    client = get_api_client()
    return await _call_api(client.list_sites)

class ListPathsParams(BaseModel):
    limit: Annotated[Optional[int], Field(description="Limit number of returned results (1-200, default 20).") ] = 20
    after: Annotated[Optional[int], Field(description="Only select paths after this ID, for pagination.")] = None

@mcp.tool(name="list_paths", description="Get an overview of paths on this site (without statistics).")
async def list_paths(params: ListPathsParams):
    client = get_api_client()
    return await _call_api(client.list_paths, limit=params.limit, after=params.after)

class StatsParams(BaseModel):
    start: Annotated[Optional[str], Field(description="Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).") ] = None
    end: Annotated[Optional[str], Field(description="End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (UTC).") ] = None
    include_paths: Annotated[Optional[list[int]], Field(description="Filter by specific path IDs.")] = None

@mcp.tool(name="get_stats_total", description="Get total number of pageviews and visitors for the site.")
async def get_stats_total(params: StatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_total,
                           start=params.start,
                           end=params.end,
                           include_paths=params.include_paths)

class PaginatedStatsParams(StatsParams):
    filter: Annotated[Optional[str], Field(description="Filter results (exact meaning depends on endpoint).") ] = None
    daily: Annotated[Optional[bool], Field(description="Group results by day instead of for the entire period (only for /stats/hits endpoint).") ] = False
    limit: Annotated[Optional[int], Field(description="Limit number of returned results (1-100, default 20).") ] = 20
    after: Annotated[Optional[int], Field(description="Pagination cursor (specific meaning depends on endpoint).") ] = None

@mcp.tool(name="get_stats_hits", description="List page statistics (pageviews and visitors per path).")
async def get_stats_hits(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_hits,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_refs", description="List referrer statistics.")
async def get_stats_refs(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_refs,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after)

@mcp.tool(name="get_stats_browsers", description="List browser statistics.")
async def get_stats_browsers(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_browsers,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after)

@mcp.tool(name="get_stats_systems", description="List operating system statistics.")
async def get_stats_systems(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_systems,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after)

@mcp.tool(name="get_stats_sizes", description="List screen size statistics.")
async def get_stats_sizes(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_sizes,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after)

@mcp.tool(name="get_stats_locations", description="List location statistics.")
async def get_stats_locations(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_locations,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after)

# Main server execution
def run():
    """Entry point for running the FastMCP server directly."""
    logger.info(f"Starting {mcp.name}...")
    # Return the coroutine to be awaited by the caller (e.g., Claude Desktop)
    return mcp.run()