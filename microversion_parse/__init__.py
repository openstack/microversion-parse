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
from collections.abc import Iterable, MutableMapping, Sequence
import dataclasses
from typing import Any, NamedTuple, Self

ENVIRON_HTTP_HEADER_FMT = 'http_{}'
STANDARD_HEADER = 'openstack-api-version'


class _VersionTuple(NamedTuple):
    major: int
    minor: int


class Version(_VersionTuple):
    """A namedtuple containing major and minor values.

    Since it is a tuple, it is automatically comparable.
    """

    max_version: tuple[int, int]
    min_version: tuple[int, int]

    def __new__(cls, major: int, minor: int) -> 'Self':
        """Add min and max version attributes to the tuple."""
        self = super().__new__(cls, major, minor)
        self.max_version = (-1, 0)
        self.min_version = (-1, 0)
        return self

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}'

    def matches(
        self,
        min_version: tuple[int, int] | None = None,
        max_version: tuple[int, int] | None = None,
    ) -> bool:
        """Is this version within min_version and max_version."""
        # NOTE(cdent): min_version and max_version are expected
        # to be set by the code that is creating the Version, if
        # they are known.
        if min_version is None:
            min_version = self.min_version
        if max_version is None:
            max_version = self.max_version
        return min_version <= self <= max_version


def _validate_version(version: object) -> Version:
    if not isinstance(version, Version):
        raise TypeError('expected a Version')
    if any(type(part) is not int or part < 0 for part in version):
        raise ValueError('version components must be non-negative integers')
    return version


@dataclasses.dataclass(frozen=True)
class VersionRange:
    """An inclusive range of concrete microversions.

    Omitted bounds are unrestricted within the supplied bound's major API
    version. At least one bound must be provided.

    :param minimum: Lower bound, or ``None`` for any minor version below
        maximum.
    :param maximum: Upper bound, or ``None`` for any minor version above
        minimum.
    :raises TypeError: A bound is not a :class:`Version`.
    :raises ValueError: Both bounds are omitted, a bound has invalid
        components, maximum < minimum, or the range spans API major versions.
    """

    minimum: Version | None = None
    maximum: Version | None = None

    def __post_init__(self) -> None:
        if self.minimum is None and self.maximum is None:
            raise ValueError('at least one version bound must be provided')

        for version in (self.minimum, self.maximum):
            if version is not None:
                _validate_version(version)

        if (
            self.minimum is not None
            and self.maximum is not None
            and self.maximum < self.minimum
        ):
            raise ValueError('maximum version is less than minimum version')

        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum.major != self.maximum.major
        ):
            # we don't allow range to span major API versions
            raise ValueError(
                'minimum and maximum versions use different major API versions'
            )

    @property
    def _major(self) -> int:
        bound = self.minimum if self.minimum is not None else self.maximum
        assert bound is not None
        return bound.major

    def __contains__(self, version: object) -> bool:
        """Return whether a concrete version falls within these bounds.

        :raises TypeError: The argument is not a :class:`Version`.
        :raises ValueError: The version has invalid components.
        """
        version = _validate_version(version)
        return (
            self.minimum is None
            or (
                self.minimum.major == version.major and self.minimum <= version
            )
        ) and (
            self.maximum is None
            or (
                self.maximum.major == version.major and version <= self.maximum
            )
        )

    def __and__(self, other: 'VersionRange') -> 'VersionRange | None':
        """Return the intersection, or ``None`` for disjoint ranges.

        Ranges with different major API versions are always disjoint.
        """
        if not isinstance(other, VersionRange):
            return NotImplemented

        if self._major != other._major:
            return None

        minimum = max(
            (v for v in (self.minimum, other.minimum) if v is not None),
            default=None,
        )
        maximum = min(
            (v for v in (self.maximum, other.maximum) if v is not None),
            default=None,
        )
        if minimum is not None and maximum is not None and minimum > maximum:
            return None

        return VersionRange(minimum, maximum)

    def overlaps(self, other: 'VersionRange') -> bool:
        """Return whether two ranges share at least one version.

        Sharing an inclusive endpoint counts as overlap. Ranges with different
        major API versions never overlap. Disjoint ranges may be adjacent or
        have a gap; this method imposes no coverage policy.
        """
        return (self & other) is not None


def get_version(
    headers: Iterable[tuple[str, str]] | MutableMapping[str, str],
    service_type: str,
    legacy_headers: Iterable[str] | None = None,
) -> str | None:
    """Parse a microversion out of headers

    If headers is not a dict we assume is an iterator of tuple-like headers,
    which we will fold into a dict.

    The flow is that we first look for the new standard singular header:

    * ``openstack-api-version: <service> <version>``

    If that's not present we fall back to the headers listed in
    ``legacy_headers``. These often look like this:

    * ``openstack-<service>-api-version: <version>``
    * ``openstack-<legacy>-api-version: <version>``
    * ``x-openstack-<legacy>-api-version: <version>``

    Folded headers are joined by ``,``.

    :param headers: The headers of a request, dict or list
    :param service_type: The service type being looked for in the headers
    :param legacy_headers: Other headers to look at for a version
    :returns: a version string or "latest"
    :raises: ValueError
    """

    folded_headers = fold_headers(headers)

    version = check_standard_header(folded_headers, service_type)
    if version:
        return version

    if legacy_headers:
        version = check_legacy_headers(folded_headers, legacy_headers)
        return version

    return None


def check_legacy_headers(
    headers: MutableMapping[str, str], legacy_headers: Iterable[str]
) -> str | None:
    """Gather values from old headers."""
    for legacy_header in legacy_headers:
        try:
            value = _extract_header_value(headers, legacy_header.lower())
            return value.split(',')[-1].strip()
        except KeyError:
            pass
    return None


def check_standard_header(
    headers: MutableMapping[str, str], service_type: str
) -> str | None:
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

    return None


# we accept Any even though we know this will be a list of 2-item tuples or a
# dict, in order to avoid reworking logic
def fold_headers(headers: Any) -> MutableMapping[str, str]:
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


def headers_from_wsgi_environ(
    environ: MutableMapping[str, str],
) -> dict[str, str]:
    """Extract all the HTTP_ keys and values from environ to a new dict.

    Note that this does not change the keys in any way in the returned dict.
    Nor is the incoming environ modified.

    :param environ: A PEP 3333 compliant WSGI environ dict.
    """
    return {key: environ[key] for key in environ if key.startswith('HTTP_')}


def _extract_header_value(
    headers: MutableMapping[str, str], header_name: str
) -> str:
    """Get the value of a header.

    The provided headers is a dict. If a key doesn't exist for ``header_name``,
    try using the WSGI environ form of the name.

    :raises: KeyError if neither key is found.
    """
    try:
        value = headers[header_name]
    except KeyError:
        wsgi_header_name = ENVIRON_HTTP_HEADER_FMT.format(
            header_name.replace('-', '_')
        )
        value = headers[wsgi_header_name]
    return value


def parse_version_string(version_string: str) -> Version:
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
        return Version(*(int(value) for value in version_string.split('.', 1)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise TypeError(f'invalid version string: {version_string}; {exc}')


def extract_version(
    headers: Iterable[tuple[str, str]] | MutableMapping[str, str],
    service_type: str,
    versions_list: Sequence[str],
) -> Version:
    """Extract the microversion from the headers.

    There may be multiple headers and some which don't match our service.

    If no version is found then the extracted version is the minimum available
    version.

    :param headers: Request headers as dict list or WSGI environ
    :param service_type: The service type as a string
    :param versions_list: List of all possible microversions as strings,
        sorted from earliest to latest version.
    :returns: a :class:`~Version` with the optional ``min_version`` and
        ``max_version`` attributes set.
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
    raise ValueError(f'Unacceptable version header: {version_string}')
