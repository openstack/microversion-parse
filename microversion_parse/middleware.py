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
"""WSGI middleware for getting microversion info."""

import webob
import webob.dec

import microversion_parse


class MicroversionMiddleware(object):
    """WSGI middleware for getting microversion info.

    The application will get a WSGI environ with a
    'SERVICE_TYPE.microversion' key that has a value of the microversion
    found at an 'openstack-api-version' header that matches SERVICE_TYPE. If
    no header is found, the minimum microversion will be set. If the
    special keyword 'latest' is used, the maximum microversion will be
    set.

    If the requested microversion is not available a 406 response is
    returned.

    If there is an error parsing a provided header, a 400 response is
    returned.

    Otherwise the application is called.
    """

    def __init__(self, application, service_type, versions,
                 json_error_formatter=None):
        """Create the WSGI middleware.

        :param application: The application hosting the service.
        :param service_type: The service type (entry in keystone catalog)
                             of the application.
        :param versions: An ordered list of legitimate versions for the
                         application.
        :param json_error_formatter: A Webob exception error formatter.
                                     See Webob for details.
        """
        self.application = application
        self.service_type = service_type
        self.microversion_environ = '%s.microversion' % service_type
        self.versions = versions
        self.json_error_formatter = json_error_formatter

    @webob.dec.wsgify
    def __call__(self, req):
        try:
            microversion = microversion_parse.extract_version(
                req.headers, self.service_type, self.versions)
        # TODO(cdent): These error response are not formatted according to
        # api-sig guidelines, unless a json_error_formatter is provided
        # that can do it. For an example, see the placement service.
        except ValueError as exc:
            raise webob.exc.HTTPNotAcceptable(
                ('Invalid microversion: %(error)s') % {'error': exc},
                json_formatter=self.json_error_formatter)
        except TypeError as exc:
            raise webob.exc.HTTPBadRequest(
                ('Invalid microversion: %(error)s') % {'error': exc},
                json_formatter=self.json_error_formatter)

        req.environ[self.microversion_environ] = microversion
        microversion_header = '%s %s' % (self.service_type, microversion)
        standard_header = microversion_parse.STANDARD_HEADER

        try:
            response = req.get_response(self.application)
        except webob.exc.HTTPError as exc:
            # If there was an HTTPError in the application we still need
            # to send the microversion header, so add the header and
            # re-raise the exception.
            exc.headers.add(standard_header, microversion_header)
            raise exc

        response.headers.add(standard_header, microversion_header)
        response.headers.add('vary', standard_header)
        return response
