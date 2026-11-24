microversion_parse
==================

A small set of functions to manage OpenStack `microversion`_ headers that can
be used in middleware, application handlers and decorators to effectively
manage microversions.

Also included, in the ``middleware`` module, is a ``MicroversionMiddleware``
that will process incoming microversion headers.

``Version``
-----------

A ``namedtuple`` with integer ``major`` and ``minor`` fields. Versions can be
compared with each other or with ``(major, minor)`` tuples, and ``str(version)``
returns the ``'major.minor'`` representation:

.. code-block:: python

    version = microversion_parse.Version(2, 10)
    assert version.major == 2
    assert version > (2, 9)
    assert str(version) == '2.10'
    assert version.matches(min_version=(2, 1), max_version=(2, 20))

``matches`` checks an inclusive range. Omitted bounds use the instance's
``min_version`` and ``max_version`` attributes, which ``extract_version`` sets
from the supported versions list. Otherwise, both attributes default to
``(-1, 0)``.

``VersionRange``
----------------

An inclusive range of concrete ``Version`` objects, useful for matching schema
or handler version bounds:

.. code-block:: python

    bounds = microversion_parse.VersionRange(
        minimum=microversion_parse.parse_version_string('2.9'),
        maximum=microversion_parse.parse_version_string('2.10'),
    )
    microversion_parse.Version(2, 9) in bounds  # True
    microversion_parse.Version(2, 10) in bounds  # True
    microversion_parse.Version(2, 11) in bounds  # False

Either bound can be omitted or set to ``None`` for an unbounded end within
that major API version. For example, a range with minimum ``Version(2, 0)``
and no maximum includes any 2.x version, but not ``Version(3, 0)``. Explicit
bounds must use the same major API version.

At least one bound must be provided; omitting both raises ``ValueError``.
Unlike ``Version.matches()``, ranges never use the ``min_version`` or
``max_version``
service bounds stored on version objects. Existing ``Version.matches()``
behavior is unchanged.

``get_version``
---------------

A simple parser for OpenStack microversion headers:

.. code-block:: python

    import microversion_parse

    # headers is a dict of headers with folded (comma-separated
    # values) or a list of header, value tuples
    version = microversion_parse.get_version(
        headers, service_type='compute',
        legacy_headers=['x-openstack-nova-api-version']
    )

    # If headers are not already available, a dict of headers
    # can be extracted from the WSGI environ
    headers = microversion_parse.headers_from_wsgi_environ(environ)
    version = microversion_parse.get_version(
        headers, service_type='placement'
    )

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

``parse_version_string``
------------------------

A function to turn a version string into a ``Version``, a comparable
``namedtuple``:

.. code-block:: python

    version_tuple = microversion_parse.parse_version_string('2.1')

If the provided string is not a valid microversion string, ``TypeError``
is raised.

``extract_version``
-------------------

Combines ``get_version`` and ``parse_version_string`` to find and validate
a microversion for a given service type in a collection of headers:

.. code-block:: python

    version_tuple = microversion_parse.extract_version(
        # a representation of headers, as accepted by get_version
        headers,
        # service type identify to match in headers
        service_type,
        # an ordered list of strings of version numbers that are the valid
        # versions presented by this service
        versions_list,
    )

``latest`` will be translated to whatever the max version is in versions_list.

If the found version is not in versions_list a ``ValueError`` is raised.

Note that ``extract_version`` does not support ``legacy_headers``.

``MicroversionMiddleware``
--------------------------

A WSGI middleware that can wrap an application that needs to be microversion
aware. The application will get a WSGI environ with a
``SERVICE_TYPE.microversion`` key that has a value of the microversion found at
an ``openstack-api-version`` header that matches ``SERVICE_TYPE``.  If no
header is found, the minimum microversion will be set. If the special keyword
``'latest'`` is used, the maximum microversion will be set.

If the requested microversion is not available a HTTP 406 response is returned.

If there is an error parsing a provided header, a HTTP 400 response is returned.

Otherwise the application is called.

The middleware is configured when it is created. Three parameters are required:

``app``
  The next WSGI middleware or application in the stack.

``service_type``
  The service type of the application, used to identify microversion headers.

``versions_list``
  An ordered list of legitimate microversions (as strings) for the application.
  It's assumed that any application that is using microversions will have such
  a list for its own housekeeping and documentation.

One named parameter is optional:

``json_error_formatter``
  A WebOb error formatter that can be used to structure the response when JSON
  is expected.

For example:

.. code-block:: python

    def app():
        app = middleware.MicroversionMiddleware(
            MyWSGIApp(), 'cats', ['1.0', '1.1', '1.2']
        )
        return app

.. _microversion: http://specs.openstack.org/openstack/api-wg/guidelines/microversion_specification.html
