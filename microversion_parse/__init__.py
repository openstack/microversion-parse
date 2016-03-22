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


STANDARD_HEADER = 'openstack-api-version'


def get_version(headers, service_type=None, legacy_type=None):
    """Parse a microversion out of headers

    :param headers: The headers of a request, dict or list
    :param service_type: The service type being looked for in the headers
    :param legacy_type: The project name to use when looking for fallback
                        headers.
    :returns: a version string or "latest"
    :raises: ValueError
    """
    # If headers is not a dict we assume is an iterator of
    # tuple-like headers, which we will fold into a dict.
    #
    # The flow is that we first look for the new standard singular
    # header:
    # * openstack-api-version: <service> <version>
    # If that's not present we fall back, in order, to:
    # * openstack-<service>-api-version: <version>
    # * openstack-<legacy>-api-version: <version>
    # * x-openstack-<legacy>-api-version: <version>
    #
    # Folded headers are joined by ,
    folded_headers = fold_headers(headers)

    version = check_standard_header(folded_headers, service_type)
    if version:
        return version

    extra_headers = build_headers(service_type, legacy_type)
    version = check_legacy_headers(folded_headers, extra_headers)
    return version


def build_headers(service_type, legacy_type=None):
    """Create the headers to be looked at."""
    headers = [
        'openstack-%s-api-version' % service_type
    ]
    if legacy_type:
        legacy_headers = [
            'openstack-%s-api-version' % legacy_type,
            'x-openstack-%s-api-version' % legacy_type
        ]
        headers.extend(legacy_headers)
    return headers


def check_legacy_headers(headers, legacy_headers):
    """Gather values from old headers."""
    for legacy_header in legacy_headers:
        try:
            value = headers[legacy_header]
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
    if isinstance(headers, dict):
        # TODO(cdent): canonicalize? (i.e. in lower())
        return headers
    header_dict = collections.defaultdict(list)
    for header, value in headers:
        header_dict[header.lower()].append(value.strip())

    folded_headers = {}
    for header, value in header_dict.items():
        folded_headers[header] = ','.join(value)

    return folded_headers
