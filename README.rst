microversion_parse
==================

A small set of functions to manage OpenStack microversion headers that can
be used in middleware, application handlers and decorators to effectively
manage microversions.

get_version
-----------

A simple parser for OpenStack microversion headers::

    import microversion_parse

    # headers is a dict of headers with folded (comma-separated
    # values) or a list of header, value tuples
    version = microversion_parse.get_version(
        headers, service_type='compute',
        legacy_headers=['x-openstack-nova-api-version'])

    # If headers are not already available, a dict of headers
    # can be extracted from the WSGI environ
    headers = microversion_parse.headers_from_wsgi_environ(environ)
    version = microversion_parse.get_version(
        headers, service_type='placement')

It processes microversion headers with the standard form::

    OpenStack-API-Version: compute 2.1

In that case, the response will be '2.1'.

If provided with a ``legacy_headers`` argument, this is treated as
a list of additional headers to check for microversions. Some examples of
headers include::

    OpenStack-telemetry-api-version: 2.1
    OpenStack-nova-api-version: 2.1
    X-OpenStack-nova-api-version: 2.1

If a version string cannot be found, ``None`` will be returned. If
the input is incorrect usual Python exceptions (ValueError,
TypeError) are allowed to raise to the caller.

parse_version_string
--------------------

A function to turn a version string into a ``Version``, a comparable
``namedtuple``::

    version_tuple = microversion_parse.parse_version_string('2.1')

If the provided string is not a valid microversion string, ``TypeError``
is raised.

extract_version
---------------

Combines ``get_version`` and ``parse_version_string`` to find and validate
a microversion for a given service type in a collection of headers::

    version_tuple = microversion_parse.extract_version(
        headers,  # a representation of headers, as accepted by get_version
        service_type,  # service type identify to match in headers
        versions_list,  # an ordered list of strings of version numbers that
                        # are the valid versions presented by this service
    )

``latest`` will be translated to whatever the max version is in versions_list.

If the found version is not in versions_list a ``ValueError`` is raised.

Note that ``extract_version`` does not support ``legacy_headers``.
