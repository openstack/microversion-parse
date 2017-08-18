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

import microversion_parse


class TestHeadersFromWSGIEnviron(testtools.TestCase):

    def test_empty_environ(self):
        environ = {}
        expected = {}
        self.assertEqual(
            expected,
            microversion_parse.headers_from_wsgi_environ(environ))

    def test_non_empty_no_headers(self):
        environ = {'PATH_INFO': '/foo/bar'}
        expected = {}
        found_headers = microversion_parse.headers_from_wsgi_environ(environ)
        self.assertEqual(expected, found_headers)

    def test_headers(self):
        environ = {'PATH_INFO': '/foo/bar',
                   'HTTP_OPENSTACK_API_VERSION': 'placement 2.1',
                   'HTTP_CONTENT_TYPE': 'application/json'}
        expected = {'HTTP_OPENSTACK_API_VERSION': 'placement 2.1',
                    'HTTP_CONTENT_TYPE': 'application/json'}
        found_headers = microversion_parse.headers_from_wsgi_environ(environ)
        self.assertEqual(expected, found_headers)

    def test_get_version_from_environ(self):
        environ = {'PATH_INFO': '/foo/bar',
                   'HTTP_OPENSTACK_API_VERSION': 'placement 2.1',
                   'HTTP_CONTENT_TYPE': 'application/json'}
        expected_version = '2.1'
        headers = microversion_parse.headers_from_wsgi_environ(environ)
        version = microversion_parse.get_version(headers, 'placement')
        self.assertEqual(expected_version, version)

    def test_get_version_from_environ_legacy(self):
        environ = {'PATH_INFO': '/foo/bar',
                   'HTTP_X_OPENSTACK_PLACEMENT_API_VERSION': '2.1',
                   'HTTP_CONTENT_TYPE': 'application/json'}
        expected_version = '2.1'
        headers = microversion_parse.headers_from_wsgi_environ(environ)
        version = microversion_parse.get_version(
            headers, 'placement',
            legacy_headers=['x-openstack-placement-api-version'])
        self.assertEqual(expected_version, version)
