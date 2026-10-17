# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.26,<2"]
# ///
"""Exercise the real stdio handshake without credentials or network calls."""
import asyncio
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root = Path(__file__).resolve().parents[1]
    env = {key: value for key, value in os.environ.items() if not key.startswith('UNIFI_')}
    params = StdioServerParameters(command='uv', args=['run', '--script', str(root / 'server.py')], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            assert {t.name for t in result.tools} == {'list_sites', 'list_clients', 'find_clients', 'get_client', 'list_devices'}
            assert all(t.annotations.readOnlyHint and not t.annotations.destructiveHint for t in result.tools)
            result = await session.call_tool('list_sites', {})
            assert result.isError
            assert 'UNIFI_BASE_URL' in str(result.content)
    print('MCP handshake, five read-only tools, and missing-configuration error passed.')


asyncio.run(main())
