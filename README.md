# UniFi Network Reader

An unofficial, read-only desktop plugin and local MCP server for UniFi Network. Discover connected clients by name, IP address, or MAC address, inspect a client, and list sites and adopted UniFi equipment. Useful for finding a vehicle, phone, or other known device on your own network.

This is not affiliated with Ubiquiti, Rivian, or Tesla. It does not install software in vehicles or control them. Connected clients only: sleeping/offline devices may not appear. A name match is a candidate, not proof of manufacturer or identity.

## Requirements and setup

- Python 3.11+ and [uv](https://docs.astral.sh/uv/).
- A UniFi Network version exposing the official Integration v1 API. The implementation was checked against the published 10.6.106 OpenAPI contract; live compatibility has not yet been verified.
- An API key with access to the chosen console. See [UniFi's authentication instructions](https://developer.ui.com/network/v9.4.17). Use the least privilege available. Never paste the key into a chat, commit it, or put it in plugin manifests.
- A trusted HTTPS certificate. For a private CA, set `UNIFI_CA_FILE` to its PEM bundle. Verification cannot be disabled by this plugin.

Set these environment variables in the environment used to launch your MCP server:

| Variable | Meaning |
| --- | --- |
| `UNIFI_BASE_URL` | Local console: `https://YOUR-CONSOLE/proxy/network/integration` |
| `UNIFI_API_KEY` | Your API key, supplied securely outside the repository |
| `UNIFI_CA_FILE` | Optional absolute path to a trusted CA bundle |

The official cloud connector can also be selected explicitly with `UNIFI_BASE_URL=https://api.ui.com/v1/connector/consoles/YOUR-CONSOLE-ID/proxy/network/integration`. Ubiquiti's documentation specifies console firmware >=5.0.3 for this connector. No automatic local/cloud fallback is performed.

The server inherits its environment; it does not automatically load `.env` files. Desktop apps launched from Finder may not inherit your terminal environment. Configure the environment using your MCP host's supported secure settings or launch the host from the configured environment.

## Run as an MCP server

Clone this repository, then register a **stdio** server in an MCP-compatible desktop host:

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "uv",
      "args": ["run", "--script", "/ABSOLUTE/PATH/unifi-network-plugin/server.py"]
    }
  }
}
```

Use an absolute path to `uv` if your desktop host cannot resolve it. `uv` installs the MCP Python SDK on first run. The checked-in script lock pins its transitive dependencies; refresh deliberately with `uv lock --script server.py`.

The root `plugin.json`, `mcp.json`, and `skills/` form a portable Agent Plugins package. For hosts supporting local plugin imports, import this folder; the packaged MCP configuration uses `${PLUGIN_ROOT}`. Host support varies. This GitHub release does **not** constitute public ChatGPT/Codex directory approval or publication. Browser-only hosts cannot directly launch this local stdio server.

## Tools

- `list_sites(offset, limit)` — Network site UUIDs.
- `list_clients(site_id, offset, limit)` — a page of connected clients.
- `find_clients(site_id, query, max_pages)` — bounded, paginated substring search of client name, IP and MAC. Reports whether it hit the page limit.
- `get_client(site_id, client_id)` — connected client details.
- `list_devices(site_id, offset, limit)` — adopted APs, switches, and other UniFi equipment.

Example: “List my UniFi sites, then find connected clients whose names contain Rivian or Tesla.” Tools return the API's data to your MCP host. Unknown/custom client names require confirmation against a known IP or MAC; the plugin does not guess vendors from MAC addresses.

## Privacy and boundaries

Only HTTPS GET requests are issued to the configured UniFi API. Redirects are rejected so the API key is not forwarded to another endpoint. Requests time out after 15 seconds, responses are capped at 4 MiB, and searches are bounded. No automatic retries, telemetry, credential storage, arbitrary endpoint tool, or network write operations are included.

Client names, IPs, MAC addresses and other returned network information are disclosed to the MCP host/assistant you choose. Its privacy policy applies. Do not publish tool outputs containing private network data. The server exposes only local stdio; it does not start a web listener.

## Development and validation

```sh
python3 -m unittest discover -s tests -v
uv run --script tests/mcp_smoke.py
```

Tests use synthetic data and mock HTTPS responses; they make no calls to a real controller. The MCP smoke test launches the server and verifies tool discovery and a credential-free error response. Live router authentication and vehicle discovery remain unverified until a user configures an API key and tests their console.

## Sources

- [Official UniFi Network API](https://developer.ui.com/network/v10.6.106/getconnectedclientoverviewpage)
- [Official plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Public directory submission and review](https://developers.openai.com/plugins/deploy/submission)

## License

MIT. See LICENSE.
