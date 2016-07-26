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


class TestFoldHeaders(testtools.TestCase):

    def test_dict_headers(self):
        headers = {
            'header-one': 'alpha',
            'header-two': 'beta',
            'header-three': 'gamma',
        }

        folded_headers = microversion_parse.fold_headers(headers)
        self.assertEqual(3, len(folded_headers))
        self.assertEqual(set(headers.keys()), set(folded_headers.keys()))
        self.assertEqual('gamma', folded_headers['header-three'])

    def test_listed_tuple_headers(self):
        headers = [
            ('header-one', 'alpha'),
            ('header-two', 'beta'),
            ('header-one', 'gamma'),
        ]

        folded_headers = microversion_parse.fold_headers(headers)
        self.assertEqual(2, len(folded_headers))
        self.assertEqual(set(['header-one', 'header-two']),
                         set(folded_headers.keys()))
        self.assertEqual('alpha,gamma', folded_headers['header-one'])

    def test_bad_headers(self):
        headers = 'wow this is not a headers'
        self.assertRaises(ValueError, microversion_parse.fold_headers,
                          headers)

    # TODO(cdent): Test with request objects from frameworks.


class TestStandardHeader(testtools.TestCase):

    def test_simple_match(self):
        headers = {
            'header-one': 'alpha',
            'openstack-api-version': 'compute 2.1',
            'header-two': 'beta',
        }
        version = microversion_parse.check_standard_header(headers, 'compute')
        # TODO(cdent): String or number. Choosing string for now
        # since 'latest' is always a string.
        self.assertEqual('2.1', version)

    def test_match_extra_whitespace(self):
        headers = {
            'header-one': 'alpha',
            'openstack-api-version': '   compute   2.1   ',
            'header-two': 'beta',
        }
        version = microversion_parse.check_standard_header(headers, 'compute')
        self.assertEqual('2.1', version)

    def test_no_match_no_value(self):
        headers = {
            'header-one': 'alpha',
            'openstack-api-version': 'compute ',
            'header-two': 'beta',
        }
        version = microversion_parse.check_standard_header(headers, 'compute')
        self.assertEqual(None, version)

    def test_no_match_wrong_service(self):
        headers = {
            'header-one': 'alpha',
            'openstack-api-version': 'network 5.9 ',
            'header-two': 'beta',
        }
        version = microversion_parse.check_standard_header(
            headers, 'compute')
        self.assertEqual(None, version)

    def test_match_multiple_services(self):
        headers = {
            'header-one': 'alpha',
            'openstack-api-version': 'network 5.9 ,compute 2.1,telemetry 7.8',
            'header-two': 'beta',
        }
        version = microversion_parse.check_standard_header(
            headers, 'compute')
        self.assertEqual('2.1', version)
        version = microversion_parse.check_standard_header(
            headers, 'telemetry')
        self.assertEqual('7.8', version)

    def test_match_multiple_same_service(self):
        headers = {
            'header-one': 'alpha',
            'openstack-api-version': 'compute 5.9 ,compute 2.1,compute 7.8',
            'header-two': 'beta',
        }
        version = microversion_parse.check_standard_header(
            headers, 'compute')
        self.assertEqual('7.8', version)


class TestLegacyHeaders(testtools.TestCase):

    def test_legacy_headers_straight(self):
        headers = {
            'header-one': 'alpha',
            'openstack-compute-api-version': ' 2.1 ',
            'header-two': 'beta',
        }
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['openstack-CoMpUte-api-version'])
        self.assertEqual('2.1', version)

    def test_legacy_headers_folded(self):
        headers = {
            'header-one': 'alpha',
            'openstack-compute-api-version': ' 2.1, 9.2 ',
            'header-two': 'beta',
        }
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['openstack-compute-api-version'])
        self.assertEqual('9.2', version)

    def test_older_legacy_headers(self):
        headers = {
            'header-one': 'alpha',
            'x-openstack-nova-api-version': ' 2.1, 9.2 ',
            'header-two': 'beta',
        }
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['openstack-nova-api-version',
                            'x-openstack-nova-api-version'])
        # We don't do x- for service types.
        self.assertEqual('9.2', version)

    def test_legacy_headers_prefer(self):
        headers = {
            'header-one': 'alpha',
            'openstack-compute-api-version': '3.7',
            'x-openstack-nova-api-version': ' 2.1, 9.2 ',
            'header-two': 'beta',
        }
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['openstack-compute-api-version',
                            'x-openstack-nova-api-version'])
        self.assertEqual('3.7', version)
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['x-openstack-nova-api-version',
                            'openstack-compute-api-version'])
        self.assertEqual('9.2', version)


class TestGetHeaders(testtools.TestCase):

    def test_preference(self):
        headers = {
            'header-one': 'alpha',
            'openstack-api-version': 'compute 11.12, telemetry 9.7',
            'openstack-compute-api-version': '3.7',
            'x-openstack-nova-api-version': ' 2.1, 9.2 ',
            'header-two': 'beta',
        }
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['openstack-compute-api-version',
                            'x-openstack-nova-api-version'])
        self.assertEqual('11.12', version)

    def test_no_headers(self):
        headers = {}
        version = microversion_parse.get_version(
            headers, service_type='compute')
        self.assertEqual(None, version)

    def test_unfolded_service(self):
        headers = [
            ('header-one', 'alpha'),
            ('openstack-api-version', 'compute 1.0'),
            ('openstack-api-version', 'compute 2.0'),
            ('openstack-api-version', '3.0'),
        ]
        version = microversion_parse.get_version(
            headers, service_type='compute')
        self.assertEqual('2.0', version)

    def test_unfolded_in_name(self):
        headers = [
            ('header-one', 'alpha'),
            ('x-openstack-nova-api-version', '1.0'),
            ('x-openstack-nova-api-version', '2.0'),
            ('openstack-telemetry-api-version', '3.0'),
        ]
        version = microversion_parse.get_version(
            headers, service_type='compute',
            legacy_headers=['x-openstack-nova-api-version'])
        self.assertEqual('2.0', version)

    def test_capitalized_headers(self):
        headers = {
            'X-Openstack-Ironic-Api-Version': '123.456'
        }
        version = microversion_parse.get_version(
            headers, service_type='ironic',
            legacy_headers=['X-Openstack-Ironic-Api-Version'])
        self.assertEqual('123.456', version)
