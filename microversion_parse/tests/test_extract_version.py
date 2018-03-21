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


class TestVersion(testtools.TestCase):

    def setUp(self):
        super(TestVersion, self).setUp()
        self.version = microversion_parse.Version(1, 5)

    def test_version_is_tuple(self):
        self.assertEqual((1, 5), self.version)

    def test_version_stringifies(self):
        self.assertEqual('1.5', str(self.version))

    def test_version_matches(self):
        max_version = microversion_parse.Version(1, 20)
        min_version = microversion_parse.Version(1, 3)

        self.assertTrue(self.version.matches(min_version, max_version))
        self.assertFalse(self.version.matches(max_version, min_version))

    def test_version_matches_inclusive(self):
        max_version = microversion_parse.Version(1, 5)
        min_version = microversion_parse.Version(1, 5)

        self.assertTrue(self.version.matches(min_version, max_version))

    def test_version_matches_no_extremes(self):
        """If no extremes are present, never match."""
        self.assertFalse(self.version.matches())

    def test_version_zero_can_match(self):
        """If a version is '0.0' we want to it be able to match."""
        version = microversion_parse.Version(0, 0)
        min_version = microversion_parse.Version(0, 0)
        max_version = microversion_parse.Version(0, 0)
        version.min_version = min_version
        version.max_version = max_version

        self.assertTrue(version.matches())

    def test_version_zero_no_defaults(self):
        """Any version, even 0.0, should never match without a min
        and max being set.
        """
        version = microversion_parse.Version(0, 0)

        self.assertFalse(version.matches())

    def test_version_init_failure(self):
        self.assertRaises(TypeError, microversion_parse.Version, 1, 2, 3)


class TestParseVersionString(testtools.TestCase):

    def test_good_version(self):
        version = microversion_parse.parse_version_string('1.1')
        self.assertEqual((1, 1), version)
        self.assertEqual(microversion_parse.Version(1, 1), version)

    def test_adapt_whitespace(self):
        version = microversion_parse.parse_version_string(' 1.1 ')
        self.assertEqual((1, 1), version)
        self.assertEqual(microversion_parse.Version(1, 1), version)

    def test_non_numeric(self):
        self.assertRaises(TypeError,
                          microversion_parse.parse_version_string,
                          'hello')

    def test_mixed_alphanumeric(self):
        self.assertRaises(TypeError,
                          microversion_parse.parse_version_string,
                          '1.a')

    def test_too_many_numeric(self):
        self.assertRaises(TypeError,
                          microversion_parse.parse_version_string,
                          '1.1.1')

    def test_not_string(self):
        self.assertRaises(TypeError,
                          microversion_parse.parse_version_string,
                          1.1)


class TestExtractVersion(testtools.TestCase):

    def setUp(self):
        super(TestExtractVersion, self).setUp()
        self.headers = [
            ('OpenStack-API-Version', 'service1 1.2'),
            ('OpenStack-API-Version', 'service2 1.5'),
            ('OpenStack-API-Version', 'service3 latest'),
            ('OpenStack-API-Version', 'service4 2.5'),
        ]
        self.version_list = ['1.1', '1.2', '1.3', '1.4',
                             '2.1', '2.2', '2.3', '2.4']

    def test_simple_extract(self):
        version = microversion_parse.extract_version(
            self.headers, 'service1', self.version_list)
        self.assertEqual((1, 2), version)

    def test_default_min(self):
        version = microversion_parse.extract_version(
            self.headers, 'notlisted', self.version_list)
        self.assertEqual((1, 1), version)

    def test_latest(self):
        version = microversion_parse.extract_version(
            self.headers, 'service3', self.version_list)
        self.assertEqual((2, 4), version)

    def test_min_max_extract(self):
        version = microversion_parse.extract_version(
            self.headers, 'service1', self.version_list)

        # below min
        self.assertFalse(version.matches((1, 3)))
        # at min
        self.assertTrue(version.matches((1, 2)))
        # within extremes
        self.assertTrue(version.matches())
        # explicit max
        self.assertTrue(version.matches(max_version=(2, 3)))
        # explicit min
        self.assertFalse(version.matches(min_version=(2, 3)))
        # explicit both
        self.assertTrue(version.matches(min_version=(0, 3),
                                        max_version=(1, 5)))

    def test_version_disabled(self):
        self.assertRaises(ValueError, microversion_parse.extract_version,
                          self.headers, 'service2', self.version_list)

    def test_version_out_of_range(self):
        self.assertRaises(ValueError, microversion_parse.extract_version,
                          self.headers, 'service4', self.version_list)
