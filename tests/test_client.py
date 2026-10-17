import io
import json
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from unifi_client import UniFiClient, UniFiError, NoRedirect

SITE = '00000000-0000-0000-0000-000000000001'
CLIENT = '00000000-0000-0000-0000-000000000002'


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = UniFiClient('https://console.example/proxy/network/integration', 'synthetic-test-key')

    def respond(self, value):
        response = Mock()
        response.read.return_value = json.dumps(value).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        self.client.opener.open = Mock(return_value=response)

    def test_only_get_and_expected_path(self):
        self.respond({'data': [], 'totalCount': 0})
        self.client.page('clients', SITE, 10, 25)
        request = self.client.opener.open.call_args.args[0]
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.full_url, f'https://console.example/proxy/network/integration/v1/sites/{SITE}/clients?offset=10&limit=25')
        self.assertEqual(request.get_header('X-api-key'), 'synthetic-test-key')

    def test_rejects_bad_config(self):
        for url in ['http://console.example/integration', 'https://key@console.example/integration',
                    'https://console.example/integration?x=1', 'https://console.example/wrong']:
            with self.subTest(url=url), self.assertRaises(UniFiError):
                UniFiClient(url, 'test')

    def test_rejects_path_injection_and_bad_pagination(self):
        for value in ['../other', None, 'default']:
            with self.assertRaises(UniFiError):
                self.client.page('clients', value)
        for offset, limit in [(-1, 1), (0, 201), (0, 0), (False, 10)]:
            with self.assertRaises(UniFiError):
                self.client.page('sites', offset=offset, limit=limit)

    def test_pagination_finds_later_matches(self):
        first = [{'name': 'Laptop'}] * 200
        second = [{'name': 'Example Rivian', 'ipAddress': '192.0.2.20'}]
        self.client.page = Mock(side_effect=[{'data': first, 'totalCount': 201}, {'data': second, 'totalCount': 201}])
        result = self.client.find_clients(SITE, 'RIVIAN')
        self.assertEqual(result['matches'], second)
        self.assertEqual(result['scanned'], 201)
        self.assertFalse(result['truncated'])
        self.assertEqual(self.client.page.call_args.kwargs['offset'], 200)

    def test_search_truncation_and_ip_mac(self):
        self.client.page = Mock(return_value={'data': [{'name': 'Custom', 'ipAddress': '192.0.2.30', 'macAddress': 'AA:BB:CC:00:00:01'}], 'totalCount': 2})
        for query in ['192.0.2.30', 'aa:bb:cc']:
            result = self.client.find_clients(SITE, query, 1)
            self.assertTrue(result['truncated'])
            self.assertEqual(len(result['matches']), 1)
        with self.assertRaises(UniFiError):
            self.client.find_clients(SITE, ' ')

    def test_errors_do_not_disclose_key_or_response(self):
        self.client.opener.open = Mock(side_effect=HTTPError('https://example.invalid', 401, 'synthetic-test-key', {}, io.BytesIO(b'private data')))
        with self.assertRaises(UniFiError) as caught:
            self.client.page('sites')
        self.assertEqual(str(caught.exception), 'API key rejected.')

    def test_rejects_redirect(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example'))

    def test_malformed_and_oversized_responses(self):
        for value in [{'data': 'bad'}, {'data': [1]}, []]:
            self.respond(value)
            with self.assertRaises(UniFiError):
                self.client.page('sites')
        response = self.client.opener.open.return_value
        response.read.return_value = b'x' * (4 * 1024 * 1024 + 1)
        with self.assertRaises(UniFiError):
            self.client.page('sites')

    def test_details_uses_validated_ids(self):
        self.respond({'id': CLIENT, 'name': 'Example'})
        self.client.client_details(SITE, CLIENT)
        self.assertTrue(self.client.opener.open.call_args.args[0].full_url.endswith(f'/sites/{SITE}/clients/{CLIENT}'))

    def test_empty_page_terminates(self):
        self.client.page = Mock(return_value={'data': [], 'totalCount': 50})
        result = self.client.find_clients(SITE, 'Tesla')
        self.assertFalse(result['truncated'])
        self.assertEqual(self.client.page.call_count, 1)


if __name__ == '__main__':
    unittest.main()
