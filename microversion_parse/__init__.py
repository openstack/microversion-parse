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

__version__ = '0.1.1'

import collections


STANDARD_HEADER = 'openstack-api-version'


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
            value = headers[legacy_header.lower()]
            return value.split(',')[-1].strip()
        except KeyError:
            pass
    return None


def check_standard_header(headers, service_type):
    """Parse the standard header to get value for service."""
    try:
        header = headers[STANDARD_HEADER]
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
    if hasattr(headers, 'keys'):
        return dict((k.lower(), v) for k, v in headers.items())
    header_dict = collections.defaultdict(list)
    for header, value in headers:
        header_dict[header.lower()].append(value.strip())

    folded_headers = {}
    for header, value in header_dict.items():
        folded_headers[header] = ','.join(value)

    return folded_headers
