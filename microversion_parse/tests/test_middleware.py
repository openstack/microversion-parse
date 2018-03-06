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

# The microversion_parse middlware is tests using gabbi to run real
# http requests through it. To do that, we need a simple WSGI
# application running under wsgi-intercept (handled by gabbi).

import os

from gabbi import driver
import webob

from microversion_parse import middleware


TESTS_DIR = 'gabbits'
SERVICE_TYPE = 'cats'
VERSIONS = [
    '1.0',  # initial version
    '1.1',  # now with kittens
    '1.2',  # added breeds
]


class SimpleWSGI(object):
    """A WSGI application that can be contiained within a middlware."""

    def __call__(self, environ, start_response):
        path_info = environ['PATH_INFO']
        if path_info == '/good':
            start_response('200 OK', [('content-type', 'text/plain')])
            return [b'good']

        raise webob.exc.HTTPNotFound('%s not found' % path_info)


def app():
    app = middleware.MicroversionMiddleware(
            SimpleWSGI(), SERVICE_TYPE, VERSIONS)
    return app


def load_tests(loader, tests, pattern):
    """Provide a TestSuite to the discovery process."""
    test_dir = os.path.join(os.path.dirname(__file__), TESTS_DIR)
    return driver.build_tests(
        test_dir, loader, test_loader_name=__name__, intercept=app)
