"""
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

import os
import string


class BackwardsFileReader(object):
    def readline(self):
        while len(self.data) == 1 and ((self.blkcount * self.blksize)
                                       < self.size):
            self.blkcount = self.blkcount + 1
            line = self.data[0]
            try:
                self._seek()
                self.data = self._read_data(line)
            except IOError:
                self.file.seek(0)
                self.data = string.split(self.file.read(self.size -
                                                        (self.blksize *
                                                         (self.blkcount - 1)))
                                         + line, self.line_feed)

        if len(self.data) == 0:
            return ""

        line = self.data[-1]
        self.data = self.data[:-1]
        return line + self.line_feed

    def _seek(self):
        self.file.seek(-self.blksize * self.blkcount, 2)

    def _read_data(self, current=None):
        if current:
            current_data = self.file.read(self.blksize) + current
        else:
            current_data = self.file.read(self.blksize)
        return string.split(current_data, self.line_feed)

    def __init__(self, file, blksize=4096):
        """initialize the internal structures"""
        self.line_feed = '\n'
        self.size = os.stat(file)[6]
        self.blksize = blksize
        self.blkcount = 1
        self.file = open(file, 'rb')
        if self.size > self.blksize:
            self._seek()
        self.data = self._read_data()
        if not self.data[-1]:
            self.data = self.data[:-1]
