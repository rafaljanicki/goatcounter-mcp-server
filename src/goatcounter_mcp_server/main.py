import os
import logging
import asyncio # Added for sleep
import random  # Added for jitter
from typing import Optional, Annotated

from pydantic import BaseModel, Field
from dotenv import load_dotenv

from fastmcp import FastMCP
from api_client import GoatcounterApiClient, GoatcounterApiClientError

# --- Configuration & Setup ---
load_dotenv() # Load environment variables from .env file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

goatcounter_code = os.getenv("GOATCOUNTER_CODE")
goatcounter_api_key = os.getenv("GOATCOUNTER_API_KEY")

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
    limit: Annotated[Optional[int], Field(description="Limit number of returned results (1-200, default 20).")] = 20
    after: Annotated[Optional[int], Field(description="Only select paths after this ID, for pagination.")] = None

@mcp.tool(name="list_paths", description="Get an overview of paths on this site (without statistics).")
async def list_paths(params: ListPathsParams):
    client = get_api_client()
    return await _call_api(client.list_paths, limit=params.limit, after=params.after)

class StatsParams(BaseModel):
    start: Annotated[Optional[str], Field(description="Start date (YYYY-MM-DD or relative e.g., '7 days ago').")] = None
    end: Annotated[Optional[str], Field(description="End date (YYYY-MM-DD or relative e.g., 'yesterday').")] = None
    filter: Annotated[Optional[str], Field(description="Filter paths (e.g., '/blog*').")] = None
    daily: Annotated[Optional[bool], Field(description="Show daily statistics instead of totals.")] = False

@mcp.tool(name="get_stats_total", description="Get total number of pageviews and visitors for the site.")
async def get_stats_total(params: StatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_total,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           daily=params.daily)

class PaginatedStatsParams(StatsParams):
    limit: Annotated[Optional[int], Field(description="Limit number of returned results (1-200, default 20).")] = 20
    after: Annotated[Optional[int], Field(description="Pagination cursor (specific meaning depends on endpoint).")] = None

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
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_browsers", description="List browser statistics.")
async def get_stats_browsers(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_browsers,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_systems", description="List operating system statistics.")
async def get_stats_systems(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_systems,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_sizes", description="List screen size statistics.")
async def get_stats_sizes(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_sizes,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_locations", description="List location statistics.")
async def get_stats_locations(params: PaginatedStatsParams):
    client = get_api_client()
    return await _call_api(client.get_stats_locations,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

# Main server execution
def run():
    """Entry point for running the FastMCP server directly."""
    logger.info(f"Starting {mcp.name}...")
    # Return the coroutine to be awaited by the caller (e.g., Claude Desktop)
    return mcp.run()