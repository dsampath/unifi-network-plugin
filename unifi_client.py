"""Read-only client for the official UniFi Network Integration API."""
import json
import os
import ssl
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, HTTPSHandler, HTTPRedirectHandler, build_opener


class UniFiError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an API key to a redirect destination.
        return None


def identifier(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise UniFiError('Site/client IDs must be UUIDs.') from None


class UniFiClient:
    def __init__(self, base_url, api_key, ca_file=None):
        parsed = urlsplit(base_url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise UniFiError('UNIFI_BASE_URL must be HTTPS without credentials, query, or fragment.')
        if not parsed.path.rstrip('/').endswith('/integration'):
            raise UniFiError('UNIFI_BASE_URL must end in /integration; see README.')
        if not api_key or '\n' in api_key or '\r' in api_key:
            raise UniFiError('Set UNIFI_API_KEY in the server environment.')
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        context = ssl.create_default_context(cafile=ca_file)
        self.opener = build_opener(HTTPSHandler(context=context), NoRedirect())

    @classmethod
    def from_env(cls):
        base = os.environ.get('UNIFI_BASE_URL', '')
        if not base:
            raise UniFiError('Set UNIFI_BASE_URL and UNIFI_API_KEY; see README.')
        return cls(base, os.environ.get('UNIFI_API_KEY', ''), os.environ.get('UNIFI_CA_FILE') or None)

    def _get(self, path, params=None):
        url = self.base_url + path
        if params:
            url += '?' + urlencode(params)
        request = Request(url, headers={'Accept': 'application/json', 'X-API-Key': self.api_key}, method='GET')
        try:
            with self.opener.open(request, timeout=15) as response:
                payload = response.read(4 * 1024 * 1024 + 1)
            if len(payload) > 4 * 1024 * 1024:
                raise UniFiError('API response exceeded 4 MiB; use a smaller page.')
            result = json.loads(payload)
            if not isinstance(result, dict):
                raise UniFiError('Unexpected API response: expected an object.')
            return result
        except HTTPError as error:
            messages = {401: 'API key rejected.', 403: 'API key lacks access.',
                        404: 'API endpoint not found; check URL and Network version.',
                        429: 'Rate limited; wait before trying again.'}
            raise UniFiError(messages.get(error.code, f'UniFi HTTP error {error.code}.')) from None
        except (URLError, TimeoutError, OSError):
            raise UniFiError('Cannot reach UniFi securely; check network, URL, and trusted CA.') from None
        except (ValueError, UnicodeError):
            raise UniFiError('UniFi returned invalid JSON.') from None

    def page(self, kind, site_id=None, offset=0, limit=100):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise UniFiError('offset must be nonnegative; limit must be 1–200.')
        if kind == 'sites':
            path = '/v1/sites'
        elif kind in ('clients', 'devices'):
            path = f'/v1/sites/{identifier(site_id)}/{kind}'
        else:
            raise UniFiError('Unsupported read operation.')
        result = self._get(path, {'offset': offset, 'limit': limit})
        if not isinstance(result.get('data'), list) or not all(isinstance(row, dict) for row in result['data']):
            raise UniFiError('Unexpected API page: expected data array of objects.')
        return result

    def client_details(self, site_id, client_id):
        return self._get(f'/v1/sites/{identifier(site_id)}/clients/{identifier(client_id)}')

    def find_clients(self, site_id, query, max_pages=20):
        if not isinstance(query, str) or not query.strip():
            raise UniFiError('Provide a nonempty name, IP, or MAC search.')
        if type(max_pages) is not int or not 1 <= max_pages <= 100:
            raise UniFiError('max_pages must be 1–100.')
        query = query.strip().casefold()
        matches, scanned = [], 0
        for _ in range(max_pages):
            page = self.page('clients', site_id, offset=scanned, limit=200)
            rows = page['data']
            matches.extend(row for row in rows if any(query in str(row.get(key, '')).casefold()
                           for key in ('name', 'ipAddress', 'macAddress')))
            scanned += len(rows)
            total = page.get('totalCount')
            if not rows or (isinstance(total, int) and scanned >= total) or (total is None and len(rows) < 200):
                return {'matches': matches, 'scanned': scanned, 'truncated': False,
                        'note': 'Connected clients only. Name matches are candidates, not verified vehicle identities.'}
        return {'matches': matches, 'scanned': scanned, 'truncated': True,
                'note': 'Page limit reached; more connected clients may exist.'}
