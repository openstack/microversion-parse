# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import testtools

from webob import headers as wb_headers

import microversion_parse


class TestWebobHeaders(testtools.TestCase):
    """Webob uses a dict-like header which is not actually a dict."""

    def test_simple_headers(self):
        headers = wb_headers.EnvironHeaders({
            'HTTP_HEADER_ONE': 'alpha',
            'HTTP_HEADER_TWO': 'beta',
            'HTTP_HEADER_THREE': 'gamma',
        })

        folded_headers = microversion_parse.fold_headers(headers)
        self.assertEqual(3, len(folded_headers))
        self.assertEqual(set(['header-one', 'header-three', 'header-two']),
                         set(folded_headers.keys()))
        self.assertEqual('gamma', folded_headers['header-three'])

    def test_simple_match(self):
        headers = wb_headers.EnvironHeaders({
            'HTTP_HEADER_ONE': 'alpha',
            'HTTP_OPENSTACK_API_VERSION': 'compute 2.1',
            'HTTP_HEADER_TWO': 'beta',
        })
        version = microversion_parse.check_standard_header(headers, 'compute')
        self.assertEqual('2.1', version)

    def test_match_multiple_services(self):
        headers = wb_headers.EnvironHeaders({
            'HTTP_HEADER_ONE': 'alpha',
            'HTTP_OPENSTACK_API_VERSION':
            'network 5.9 ,compute 2.1,telemetry 7.8',
            'HTTP_HEADER_TWO': 'beta',
        })
        version = microversion_parse.check_standard_header(
            headers, 'compute')
        self.assertEqual('2.1', version)
        version = microversion_parse.check_standard_header(
            headers, 'telemetry')
        self.assertEqual('7.8', version)

    def test_legacy_headers_straight(self):
        headers = wb_headers.EnvironHeaders({
            'HTTP_HEADER_ONE': 'alpha',
            'HTTP_X_OPENSTACK_NOVA_API_VERSION': ' 2.1 ',
            'HTTP_HEADER_TWO': 'beta',
        })
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['x-openstack-nova-api-version'])
        self.assertEqual('2.1', version)

    def test_legacy_headers_folded(self):
        headers = wb_headers.EnvironHeaders({
            'HTTP_HEADER_ONE': 'alpha',
            'HTTP_X_OPENSTACK_NOVA_API_VERSION': ' 2.1, 9.2 ',
            'HTTP_HEADER_TWO': 'beta',
        })
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['x-openstack-nova-api-version'])
        self.assertEqual('9.2', version)
