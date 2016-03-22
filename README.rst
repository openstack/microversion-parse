microversion_parse
=================

A simple parser for OpenStack microversion headers::

    import microversion_parse

    # headers is a dict of headers with folded (comma-separated
    # values) or a list of header, value tuples
    version = microversion_parse.get_version(
        headers, service_type='compute', legacy_type='nova')

It processes microversion headers with the standard form::

    OpenStack-API-Version: compute 2.1

It also deals with several older formats, depending on the values of
the service_type and legacy_type arguments::

    OpenStack-compute-api-version: 2.1
    OpenStack-nova-api-version: 2.1
    X-OpenStack-nova-api-version: 2.1

.. note:: The X prefixed version does not currently parse for
          service type named headers, only project named headers.

If a version string cannot be found ``None`` will be returned. If
the input is incorrect usual Python exceptions (ValueError,
TypeError) are allowed to raise to the caller.
