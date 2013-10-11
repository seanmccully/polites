"""
(c) 2013 Sean McCully
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
"""
import logging
import sys
from xml.etree import ElementTree

from polites.exceptions import PolitesException
from twisted.internet import reactor
from twisted.web.client import getPage

LOG = logging.getLogger(__name__)

class PolitesClient(object):
    """CLI interace for running Polite Commands.

        Args:
            config - Polites Config Object.
            command - command to run
            func - command function to call
    """

    url = "http://%s:%s/%s"
    commands = ["status", "restart", "snapshot", "restore"]
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    def __init__(self, config, command=None, func=None):
        self.config = config
        if func:
            getattr(self, func.im_func.func_name)()
        if command and command in command in PolitesClient.commands:
            getattr(self, command,
                    lambda: PolitesException("Invalid Client Command"))()

    def _make_request(self, paths, method=None, data=None):
        """Makes http request.

            Args:
                path - http path for request.
                method - http method for request.
                data - data for http POST/PUT method(s).
        """
        kwargs = {'headers': PolitesClient.headers}
        if method:
            kwargs['method'] = method
            if data:
                kwargs['postdata'] = data

        curr = sys._getframe(0)
        fname = curr.f_back.f_code.co_name
        callback = getattr(self, fname + '_callback')
        if type(paths) == str:
            url = PolitesClient.url % (self.config.hostname,
                                       self.config.default_web_port,
                                       paths)
            deferred = getPage(url, **kwargs)
            self.add_cb(deferred, callback)
        else:
            for path in paths:
                url = PolitesClient.url % (self.config.hostname,
                                           self.config.default_web_port,
                                           path)
                deferred = getPage(url, **kwargs)
                deferred.addCallback(callback)
            self.add_cb(deferred)

    def _get_func_name(self, func):
        return func.im_func.func_name

    def status_callback(self, response):
        """Callback Method for printing response.

            Args:
                response - data to print to stdout.
        """
        print response

    def status(self):
        """Gets status."""
        self._make_request(('', PolitesClient.commands[2], ))

    def restart(self):
        """Performs Restart."""
        setattr(self, 'restart_callback', self.status_callback)
        self._make_request('', method='POST', data='restart=True')

    def snapshot(self):
        """Performs Restart."""
        setattr(self, 'snapshot_callback', self.status_callback)
        self._make_request(PolitesClient.commands[-2], method='PUT')

    def restore(self):
        """Starts Restore from snapshot."""
        url = PolitesClient.url % (self.config.hostname,
                                   self.config.default_web_port,
                                   PolitesClient.commands[-2])
        deferred = getPage(url)
        deferred.addCallback(self.restore_next)
        deferred.addErrback(self.error_end)

    def restore_next(self, response):
        """Receives response from snapshot command. For Restore Point.

            Args:
                response - response text to evaulate.
        """
        doc = ElementTree.fromstring(response)
        element = doc.find('last-snapshot')
        if element.text:
            setattr(self, 'restore_next_callback', self.status_callback)
            self._make_request('restore', method='POST',
                               data='snapshot-name=%s' % element.text)


    def add_cb(self, deferred, callback_func=None):
        """Method for adding callback func.

            Args:
                deferred - deferred callbacks added to.
                callback_func - function to add as callback.
        """
        if callback_func:
            deferred.addCallback(callback_func)
        deferred.addCallback(self.end)
        deferred.addErrback(self.error_end)

    def end(self, *args):
        reactor.stop()

    def error_end(self, error):
        self.end()
        if error:
            error.raiseException()
