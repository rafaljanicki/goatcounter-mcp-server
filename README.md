# Goatcounter MCP Server

[![smithery badge](https://smithery.ai/badge/@rafaljanicki/goatcounter-mcp-server)](https://smithery.ai/server/@rafaljanicki/goatcounter-mcp-server)

## Overview

This project provides a Model Context Protocol (MCP) server for interacting with the [Goatcounter](https://www.goatcounter.com/) web analytics API. It allows language models or other MCP clients to easily query Goatcounter statistics and information using a standardized tool interface.

The server is built using Python and the [FastMCP](https://github.com/metr/fastmcp) library. It reads your Goatcounter site code and API key from environment variables for authentication.

## Features

*   Provides tools for most Goatcounter API endpoints.
*   Handles API key and site code configuration via environment variables (`GOATCOUNTER_API_KEY`, `GOATCOUNTER_CODE`).
*   Lazy initialization of the API client: Tools can be listed even if API credentials are not yet configured.
*   **Rate Limit Handling**: Implements automatic retries with backoff when encountering API rate limits (HTTP 429).
    *   Prioritizes the `X-Rate-Limit-Reset` header for waiting if provided by the API.
    *   Falls back to exponential backoff (starting at 1 second) with random jitter if the header is unavailable or invalid.
    *   Retries up to 5 times before failing.
*   Runs directly using the `fastmcp` command-line tool.

## Installation

### Option 1: Installing via Smithery (Recommended)

To install X (Twitter) MCP server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/goatcounter-mcp-server):

```bash
npx -y @smithery/cli install @rafaljanicki/goatcounter-mcp-server --client claude
```

### Option 2: Install from PyPI
The easiest way to install `goatcounter-mcp-server` is via PyPI:

```bash
pip install goatcounter-mcp-server
```

Or install directly from the repository:

```bash
pip install git+https://github.com/rafaljanicki/goatcounter-mcp-server.git
```

### Option 3: Install from Source
If you prefer to install from the source repository:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/rafaljanicki/goatcounter-mcp-server
    cd goatcounter-mcp-server
    ```

2.  **Create a virtual environment:**
    ```bash
    python3.13 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    Install FastMCP and other required packages:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Copy the example `.env.example` file to `.env`:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your Goatcounter details (see Environment Variables section below).

## Environment Variables

The server requires the following environment variables to be set:

*   `GOATCOUNTER_CODE`: Your Goatcounter site code (the subdomain part, e.g., 'mycoolsite').
*   `GOATCOUNTER_API_KEY`: Your Goatcounter API token. You can generate one in your Goatcounter site under Settings -> API tokens. Ensure it has the necessary permissions for the API actions you intend to use.

You can set these variables directly in your environment or place them in a `.env` file in the project root.

## Running the Server

### Option 1: Using the CLI Script
The project defines a CLI script `goatcounter-mcp-server`.

If installed from PyPI:
```bash
goatcounter-mcp-server
```

If installed from source with `uv`:
```bash
uv run goatcounter-mcp-server
```

### Option 2: Using FastMCP Directly (Source Only)
If you installed from source and prefer to run the server using FastMCP's development mode:

```bash
fastmcp dev src/goatcounter_mcp_server/server.py
```

## Using with Claude Desktop

To use this MCP server with Claude Desktop, you need to configure Claude to connect to the server. Follow these steps:

### Step 1: Install Node.js
Claude Desktop uses Node.js to run MCP servers. If you don't have Node.js installed:
- Download and install Node.js from [nodejs.org](https://nodejs.org/).
- Verify installation:
  ```bash
  node --version
  ```

### Step 2: Locate Claude Desktop Configuration
Claude Desktop uses a `claude_desktop_config.json` file to configure MCP servers.

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

If the file doesn't exist, create it.

### Step 3: Configure the MCP Server
Edit `claude_desktop_config.json` to include the `goatcounter-mcp-server` server. Replace `/path/to/goatcounter-mcp-server` with the actual path to your project directory (if installed from source) or the path to your Python executable (if installed from PyPI).

If installed from PyPI:
```json
{
  "mcpServers": {
    "goatcounter-mcp-server": {
      "command": "goatcounter-mcp-server",
      "args": [],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "GOATCOUNTER_CODE": "goatcounter_code",
        "GOATCOUNTER_API_KEY": "goatcounter_api_key"
      }
    }
  }
}
```

If installed from source with `uv`:
```json
{
  "mcpServers": {
    "goatcounter-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/goatcounter-mcp-server",
        "run",
        "goatcounter-mcp-server"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "GOATCOUNTER_CODE": "goatcounter_code",
        "GOATCOUNTER_API_KEY": "goatcounter_api_key"
      }
    }
  }
}
```

- `"command": "goatcounter-mcp-server"`: Uses the CLI script directly if installed from PyPI.
- `"env"`: If installed from PyPI, you may need to provide environment variables directly in the config (since there's no `.env` file). If installed from source, the `.env` file will be used.
- `"env": {"PYTHONUNBUFFERED": "1"}`: Ensures output is unbuffered for better logging in Claude.

### Step 4: Restart Claude Desktop
- Quit Claude Desktop completely.
- Reopen Claude Desktop to load the new configuration.

### Step 5: Verify Connection
- Open Claude Desktop.
- Look for a hammer or connector icon in the input area (bottom right corner). This indicates MCP tools are available.
- Click the icon to see the available tools from `goatcounter-mcp-server`

## API Documentation: Available Tools

The following MCP tools are available:

---

### Tool: `Goatcounter_get_me`

Get information about the current Goatcounter user and API key associated with the configured `GOATCOUNTER_API_KEY`.

*   **Parameters**: None
*   **Returns**: `object` - Information about the user and token.

---

### Tool: `Goatcounter_list_sites`

List all Goatcounter sites accessible with the current API key.

*   **Parameters**: None
*   **Returns**: `object` - A list of accessible sites.

---

### Tool: `Goatcounter_list_paths`

Get an overview of paths tracked on this site (without statistics).

*   **Parameters**:
    *   `limit` (integer, optional): Limit number of returned results (1-200, default 20).
    *   `after` (integer, optional): Only select paths after this path ID, for pagination.
*   **Returns**: `object` - A list of paths and pagination info.

---

### Tool: `Goatcounter_get_stats_total`

Get the total number of pageviews and unique visitors for the site within a specified period.

*   **Parameters**:
    *   `start` (string, optional): Start date (YYYY-MM-DD or relative e.g., '7 days ago').
    *   `end` (string, optional): End date (YYYY-MM-DD or relative e.g., 'yesterday').
    *   `filter` (string, optional): Filter paths (e.g., '/blog*').
    *   `daily` (boolean, optional): Show daily statistics instead of totals (default: false).
*   **Returns**: `object` - Total statistics or daily statistics if `daily` is true.

---

### Tool: `Goatcounter_get_stats_hits`

List page statistics (pageviews and visitors per path).

*   **Parameters**:
    *   `start` (string, optional): Start date (YYYY-MM-DD or relative e.g., '7 days ago').
    *   `end` (string, optional): End date (YYYY-MM-DD or relative e.g., 'yesterday').
    *   `filter` (string, optional): Filter paths (e.g., '/blog*').
    *   `daily` (boolean, optional): Show daily statistics instead of totals (default: false).
    *   `limit` (integer, optional): Limit number of returned results (1-200, default 20).
    *   `after` (integer, optional): Pagination cursor.
*   **Returns**: `object` - A list of path statistics and pagination info.

---

### Tool: `Goatcounter_get_stats_refs`

List referrer statistics.

*   **Parameters**:
    *   `start` (string, optional): Start date (YYYY-MM-DD or relative e.g., '7 days ago').
    *   `end` (string, optional): End date (YYYY-MM-DD or relative e.g., 'yesterday').
    *   `filter` (string, optional): Filter paths (e.g., '/blog*').
    *   `daily` (boolean, optional): Show daily statistics instead of totals (default: false).
    *   `limit` (integer, optional): Limit number of returned results (1-200, default 20).
    *   `after` (integer, optional): Pagination cursor.
*   **Returns**: `object` - A list of referrer statistics and pagination info.

---

### Tool: `Goatcounter_get_stats_browsers`

List browser statistics.

*   **Parameters**:
    *   `start` (string, optional): Start date (YYYY-MM-DD or relative e.g., '7 days ago').
    *   `end` (string, optional): End date (YYYY-MM-DD or relative e.g., 'yesterday').
    *   `filter` (string, optional): Filter paths (e.g., '/blog*').
    *   `daily` (boolean, optional): Show daily statistics instead of totals (default: false).
    *   `limit` (integer, optional): Limit number of returned results (1-200, default 20).
    *   `after` (integer, optional): Pagination cursor.
*   **Returns**: `object` - A list of browser statistics and pagination info.

---

### Tool: `Goatcounter_get_stats_systems`

List operating system statistics.

*   **Parameters**:
    *   `start` (string, optional): Start date (YYYY-MM-DD or relative e.g., '7 days ago').
    *   `end` (string, optional): End date (YYYY-MM-DD or relative e.g., 'yesterday').
    *   `filter` (string, optional): Filter paths (e.g., '/blog*').
    *   `daily` (boolean, optional): Show daily statistics instead of totals (default: false).
    *   `limit` (integer, optional): Limit number of returned results (1-200, default 20).
    *   `after` (integer, optional): Pagination cursor.
*   **Returns**: `object` - A list of OS statistics and pagination info.

---

### Tool: `Goatcounter_get_stats_sizes`

List screen size statistics.

*   **Parameters**:
    *   `start` (string, optional): Start date (YYYY-MM-DD or relative e.g., '7 days ago').
    *   `end` (string, optional): End date (YYYY-MM-DD or relative e.g., 'yesterday').
    *   `filter` (string, optional): Filter paths (e.g., '/blog*').
    *   `daily` (boolean, optional): Show daily statistics instead of totals (default: false).
    *   `limit` (integer, optional): Limit number of returned results (1-200, default 20).
    *   `after` (integer, optional): Pagination cursor.
*   **Returns**: `object` - A list of screen size statistics and pagination info.

---

### Tool: `Goatcounter_get_stats_locations`

List location statistics.

*   **Parameters**:
    *   `start` (string, optional): Start date (YYYY-MM-DD or relative e.g., '7 days ago').
    *   `end` (string, optional): End date (YYYY-MM-DD or relative e.g., 'yesterday').
    *   `filter` (string, optional): Filter paths (e.g., '/blog*').
    *   `daily` (boolean, optional): Show daily statistics instead of totals (default: false).
    *   `limit` (integer, optional): Limit number of returned results (1-200, default 20).
    *   `after` (integer, optional): Pagination cursor.
*   **Returns**: `object` - A list of location statistics and pagination info.

## Usage

1.  **Set Environment Variables:**
    Create a `.env` file in your project root or set the environment variables directly:
    ```
    GOATCOUNTER_CODE=your_site_code
    GOATCOUNTER_API_KEY=your_goatcounter_api_key
    ```
    You can generate an API key in your Goatcounter account settings.

2.  **Run with FastMCP:**
    Integrate this server with your FastMCP setup. Refer to the FastMCP documentation for details on connecting MCP servers.

    The server registers tools with the prefix `Goatcounter` (e.g., `Goatcounter.list_sites`).

## Development

*   Install development dependencies: `pip install -e ".[dev]"` (if dev dependencies are specified in `pyproject.toml`)
*   This project uses `hatch` for building.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 