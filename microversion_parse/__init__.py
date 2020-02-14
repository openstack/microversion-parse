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

import collections


ENVIRON_HTTP_HEADER_FMT = 'http_{}'
STANDARD_HEADER = 'openstack-api-version'


class Version(collections.namedtuple('Version', 'major minor')):
    """A namedtuple containing major and minor values.

    Since it is a tuple, it is automatically comparable.
    """

    def __new__(cls, major, minor):
        """Add min and max version attributes to the tuple."""
        self = super(Version, cls).__new__(cls, major, minor)
        self.max_version = (-1, 0)
        self.min_version = (-1, 0)
        return self

    def __str__(self):
        return '%s.%s' % (self.major, self.minor)

    def matches(self, min_version=None, max_version=None):
        """Is this version within min_version and max_version.
        """
        # NOTE(cdent): min_version and max_version are expected
        # to be set by the code that is creating the Version, if
        # they are known.
        if min_version is None:
            min_version = self.min_version
        if max_version is None:
            max_version = self.max_version
        return min_version <= self <= max_version


def get_version(headers, service_type, legacy_headers=None):
    """Parse a microversion out of headers

    :param headers: The headers of a request, dict or list
    :param service_type: The service type being looked for in the headers
    :param legacy_headers: Other headers to look at for a version
    :returns: a version string or "latest"
    :raises: ValueError

    If headers is not a dict we assume is an iterator of
    tuple-like headers, which we will fold into a dict.

    The flow is that we first look for the new standard singular
    header:

    * openstack-api-version: <service> <version>

    If that's not present we fall back to the headers listed in
    legacy_headers. These often look like this:

    * openstack-<service>-api-version: <version>
    * openstack-<legacy>-api-version: <version>
    * x-openstack-<legacy>-api-version: <version>

    Folded headers are joined by ','.
    """

    folded_headers = fold_headers(headers)

    version = check_standard_header(folded_headers, service_type)
    if version:
        return version

    if legacy_headers:
        version = check_legacy_headers(folded_headers, legacy_headers)
        return version

    return None


def check_legacy_headers(headers, legacy_headers):
    """Gather values from old headers."""
    for legacy_header in legacy_headers:
        try:
            value = _extract_header_value(headers, legacy_header.lower())
            return value.split(',')[-1].strip()
        except KeyError:
            pass
    return None


def check_standard_header(headers, service_type):
    """Parse the standard header to get value for service."""
    try:
        header = _extract_header_value(headers, STANDARD_HEADER)
        for header_value in reversed(header.split(',')):
            try:
                service, version = header_value.strip().split(None, 1)
                if service.lower() == service_type.lower():
                    return version.strip()
            except ValueError:
                pass
    except (KeyError, ValueError):
        return None


def fold_headers(headers):
    """Turn a list of headers into a folded dict."""
    # If it behaves like a dict, return it. Webob uses objects which
    # are not dicts, but behave like them.
    try:
        return dict((k.lower(), v) for k, v in headers.items())
    except AttributeError:
        pass
    header_dict = collections.defaultdict(list)
    for header, value in headers:
        header_dict[header.lower()].append(value.strip())

    folded_headers = {}
    for header, value in header_dict.items():
        folded_headers[header] = ','.join(value)

    return folded_headers


def headers_from_wsgi_environ(environ):
    """Extract all the HTTP_ keys and values from environ to a new dict.

    Note that this does not change the keys in any way in the returned
    dict. Nor is the incoming environ modified.

    :param environ: A PEP 3333 compliant WSGI environ dict.
    """
    return {key: environ[key] for key in environ if key.startswith('HTTP_')}


def _extract_header_value(headers, header_name):
    """Get the value of a header.

    The provided headers is a dict. If a key doesn't exist for
    header_name, try using the WSGI environ form of the name.

    Raises KeyError if neither key is found.
    """
    try:
        value = headers[header_name]
    except KeyError:
        wsgi_header_name = ENVIRON_HTTP_HEADER_FMT.format(
            header_name.replace('-', '_'))
        value = headers[wsgi_header_name]
    return value


def parse_version_string(version_string):
    """Turn a version string into a Version

    :param version_string: A string of two numerals, X.Y.
    :returns: a Version
    :raises: TypeError
    """
    try:
        # The combination of int and a limited split with the
        # named tuple means that this incantation will raise
        # ValueError, TypeError or AttributeError when the incoming
        # data is poorly formed but will, however, naturally adapt to
        # extraneous whitespace.
        return Version(*(int(value) for value
                         in version_string.split('.', 1)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise TypeError('invalid version string: %s; %s' % (
            version_string, exc))


def extract_version(headers, service_type, versions_list):
    """Extract the microversion from the headers.

    There may be multiple headers and some which don't match our
    service.

    If no version is found then the extracted version is the minimum
    available version.

    :param headers: Request headers as dict list or WSGI environ
    :param service_type: The service_type as a string
    :param versions_list: List of all possible microversions as strings,
                          sorted from earliest to latest version.
    :returns: a Version with the optional min_version and max_version
              attributes set.
    :raises: ValueError
    """
    found_version = get_version(headers, service_type=service_type)
    min_version_string = versions_list[0]
    max_version_string = versions_list[-1]

    # If there was no version found in the headers, choose the minimum
    # available version.
    version_string = found_version or min_version_string
    if version_string == 'latest':
        version_string = max_version_string
    request_version = parse_version_string(version_string)
    request_version.max_version = parse_version_string(max_version_string)
    request_version.min_version = parse_version_string(min_version_string)
    # We need a version that is in versions_list. This gives us the option
    # to administratively disable a version if we really need to.
    if str(request_version) in versions_list:
        return request_version
    raise ValueError('Unacceptable version header: %s' % version_string)
