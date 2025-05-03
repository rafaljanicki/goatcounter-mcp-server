import os
import logging
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

if not goatcounter_code:
    raise ValueError("GOATCOUNTER_CODE environment variable not set.")
if not goatcounter_api_key:
    raise ValueError("GOATCOUNTER_API_KEY environment variable not set.")

# --- Initialize API Client ---
# Note: In this simplified setup without FastAPI lifespan, the client is created
# globally and closed implicitly when the process exits.
api_client = GoatcounterApiClient(site_code=goatcounter_code, api_key=goatcounter_api_key)

# --- FastMCP Instance ---
mcp = FastMCP(
    name="GoatcounterMCP",
    description="MCP server for interacting with the Goatcounter API.",
    prefix="Goatcounter"
)

# --- Helper Function for Error Handling ---
async def _call_api(api_method, **kwargs):
    try:
        result = await api_method(**kwargs)
        # Ensure None is returned correctly if API gives 202/204
        return result if result is not None else {}
    except GoatcounterApiClientError as e:
        logger.error(f"Goatcounter API Client Error: {e}")
        # Raise a standard exception, FastMCP will handle formatting
        raise Exception(f"Goatcounter API Error: {e}") from e
    except Exception as e:
        logger.exception(f"Unexpected error calling Goatcounter API: {e}")
        raise Exception(f"An unexpected internal server error occurred: {e}")

# --- MCP Tool Definitions ---

@mcp.tool(name="get_me", description="Get information about the current Goatcounter user and API key.")
async def get_me():
    return await _call_api(api_client.get_me)

@mcp.tool(name="list_sites", description="List all Goatcounter sites accessible with the current API key.")
async def list_sites():
    return await _call_api(api_client.list_sites)

class ListPathsParams(BaseModel):
    limit: Annotated[Optional[int], Field(description="Limit number of returned results (1-200, default 20).")] = 20
    after: Annotated[Optional[int], Field(description="Only select paths after this ID, for pagination.")] = None

@mcp.tool(name="list_paths", description="Get an overview of paths on this site (without statistics).")
async def list_paths(params: ListPathsParams):
    return await _call_api(api_client.list_paths, limit=params.limit, after=params.after)

class StatsParams(BaseModel):
    start: Annotated[Optional[str], Field(description="Start date (YYYY-MM-DD or relative e.g., '7 days ago').")] = None
    end: Annotated[Optional[str], Field(description="End date (YYYY-MM-DD or relative e.g., 'yesterday').")] = None
    filter: Annotated[Optional[str], Field(description="Filter paths (e.g., '/blog*').")] = None
    daily: Annotated[Optional[bool], Field(description="Show daily statistics instead of totals.")] = False

@mcp.tool(name="get_stats_total", description="Get total number of pageviews and visitors for the site.")
async def get_stats_total(params: StatsParams):
    return await _call_api(api_client.get_stats_total,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           daily=params.daily)

class PaginatedStatsParams(StatsParams):
    limit: Annotated[Optional[int], Field(description="Limit number of returned results (1-200, default 20).")] = 20
    after: Annotated[Optional[int], Field(description="Pagination cursor (specific meaning depends on endpoint).")] = None

@mcp.tool(name="get_stats_hits", description="List page statistics (pageviews and visitors per path).")
async def get_stats_hits(params: PaginatedStatsParams):
    return await _call_api(api_client.get_stats_hits,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_refs", description="List referrer statistics.")
async def get_stats_refs(params: PaginatedStatsParams):
    return await _call_api(api_client.get_stats_refs,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_browsers", description="List browser statistics.")
async def get_stats_browsers(params: PaginatedStatsParams):
    return await _call_api(api_client.get_stats_browsers,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_systems", description="List operating system statistics.")
async def get_stats_systems(params: PaginatedStatsParams):
    return await _call_api(api_client.get_stats_systems,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_sizes", description="List screen size statistics.")
async def get_stats_sizes(params: PaginatedStatsParams):
    return await _call_api(api_client.get_stats_sizes,
                           start=params.start,
                           end=params.end,
                           filter=params.filter,
                           limit=params.limit,
                           after=params.after,
                           daily=params.daily)

@mcp.tool(name="get_stats_locations", description="List location statistics.")
async def get_stats_locations(params: PaginatedStatsParams):
    return await _call_api(api_client.get_stats_locations,
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