# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.26,<2"]
# ///
"""Local stdio MCP server. No network mutations or credential storage."""
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from unifi_client import UniFiClient

mcp = FastMCP('UniFi Network Reader')
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)


@mcp.tool(annotations=READ)
def list_sites(offset: int = 0, limit: int = 100) -> dict:
    """List Network application sites. Use returned site UUIDs for other tools."""
    return UniFiClient.from_env().page('sites', offset=offset, limit=limit)


@mcp.tool(annotations=READ)
def list_clients(site_id: str, offset: int = 0, limit: int = 100) -> dict:
    """List connected clients, including names, IP/MAC addresses and connection types."""
    return UniFiClient.from_env().page('clients', site_id, offset, limit)


@mcp.tool(annotations=READ)
def find_clients(site_id: str, query: str, max_pages: int = 20) -> dict:
    """Search connected clients by name, IP or MAC (case insensitive). Reports truncation.

    A Rivian or Tesla name match is only a candidate. Offline clients are not returned.
    """
    return UniFiClient.from_env().find_clients(site_id, query, max_pages)


@mcp.tool(annotations=READ)
def get_client(site_id: str, client_id: str) -> dict:
    """Get details for a connected client using site and client UUIDs."""
    return UniFiClient.from_env().client_details(site_id, client_id)


@mcp.tool(annotations=READ)
def list_devices(site_id: str, offset: int = 0, limit: int = 100) -> dict:
    """List adopted UniFi equipment such as APs and switches; these are not client devices."""
    return UniFiClient.from_env().page('devices', site_id, offset, limit)


if __name__ == '__main__':
    mcp.run(transport='stdio')
