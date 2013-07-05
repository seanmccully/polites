import os
import string

"""read a file returning the lines in reverse order for each call of readline()
This actually just reads blocks (4096 bytes by default) of data from the end of
the file and returns last line in an internal buffer.  I believe all the corner
cases are handled, but never can be sure..."""

class BackwardsReader:
    def readline(self):
        while len(self.data) == 1 and ((self.blkcount * self.blksize) < self.size):
            self.blkcount = self.blkcount + 1
            line = self.data[0]
            try:
                self.f.seek(-self.blksize * self.blkcount, 2) # read from end of file
                self.data = string.split(self.f.read(self.blksize) + line, '\n')
            except IOError:  # can't seek before the beginning of the file
                self.f.seek(0)
                self.data = string.split(self.f.read(self.size - (self.blksize * (self.blkcount-1))) + line, '\n')

        if len(self.data) == 0:
            return ""

        # self.data.pop()
        # make it compatible with python <= 1.5.1
        line = self.data[-1]
        self.data = self.data[:-1]
        return line + '\n'

    def __init__(self, file, blksize=4096):
        """initialize the internal structures"""
        # get the file size
        self.size = os.stat(file)[6]
        # how big of a block to read from the file...
        self.blksize = blksize
        # how many blocks we've read
        self.blkcount = 1
        self.f = open(file, 'rb')
        # if the file is smaller than the blocksize, read a block,
        # otherwise, read the whole thing...
        if self.size > self.blksize:
            self.f.seek(-self.blksize * self.blkcount, 2) # read from end of file
        self.data = string.split(self.f.read(self.blksize), '\n')
        # strip the last item if it's empty...  a byproduct of the last line having
        # a newline at the end of it
        if not self.data[-1]:
        # self.data.pop()
            self.data = self.data[:-1]

