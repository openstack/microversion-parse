microversion_parse
==================

A simple parser for OpenStack microversion headers::

    import microversion_parse

    # headers is a dict of headers with folded (comma-separated
    # values) or a list of header, value tuples
    version = microversion_parse.get_version(
        headers, service_type='compute',
        legacy_headers=['x-openstack-nova-api-version'])

It processes microversion headers with the standard form::

    OpenStack-API-Version: compute 2.1

If provided with a ``legacy_headers`` argument, this is treated as
a list of headers to check for microversions. Some examples of
headers include::

    OpenStack-telemetry-api-version: 2.1
    OpenStack-nova-api-version: 2.1
    X-OpenStack-nova-api-version: 2.1

If a version string cannot be found, ``None`` will be returned. If
the input is incorrect usual Python exceptions (ValueError,
TypeError) are allowed to raise to the caller.
