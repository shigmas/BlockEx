import http.client

import ssl


class StreamContext(object):
    def __init__(self):
        self.contextReset()

    def contextReset(self):
        self._lines = []
        # self._outputStream = open('webout',"w", encoding='utf-8')

    def bufferLine(self, line):
        self._lines.append(line)
        # self._outputStream.write(line)

    def getCurrentLineNumber(self):
        return len(self._lines) - 1

    def getLineAt(self, number):
        if number < len(self._lines):
            return self._lines[number]
        else:
            print('%s beyond index' % number)
            return None

    def closeContext(self):
        # self._outputStream.close()
        pass


class StreamParser(object):
    # line was not handled by the block
    BlockNotHandled = 0
    # line was handled by the block
    BlockHandled    = 1
    # line was handled and no more processing should be done
    BlockShouldExit = 2

    def __init__(self):
        self.blockMatchers = []
        self.currentMatchers = []
        self.isCooperative = True
        self._errors = open('errors', "w", encoding='utf-8')
        self.reset()

    def reset(self):
        for matcher in self.blockMatchers:
            matcher.reset()
        self.currentMatchers = []
        self.encoding = 'utf-8'
        self.inputStream = None
        self.outputStream = None
        self.status = 0
        self.reason = None
        self.forceConnectionClose = False

    def completeParsing(self):
        self._completeParsing()
        if isinstance(self, StreamContext):
            self.bufferLine(self._getNextLine())
        self._errors.close()

    # Subclasses implement this function. This gets called when the BlockBase
    # "wants" the line, not just on a match. _handleLine can know if it is
    # called on a match if there is actually match data to process.
    def _handleLine(self, matcher):
        # for concrete subclasses that want data from the line (versus the ones
        # that only want to read the file in and write it out), we have this
        # hook to parse out the line.
        return False

    def _getNextLine(self):
        line = self.inputStream.readline()
        # if line is a byte-type, we need to convert it to unicode. I believe
        # readline was returning bytes (Python 2.x?), but if it returns
        # a string, we don't need convert again.
        if isinstance(line, str):
            return line
        else:
            ret = ''
            try:
                ret = str(line, encoding=self.encoding)
            except UnicodeDecodeError as uniErr:
                print('UnicodeDecodeError: %s' % uniErr)
                self._errors.write('%s [%s]' % (uniErr, line))
            return ret

    # line: the line in the stream to process
    # block: the BlockBase.
    def _processBlock(self, line, block):
        handled = self.BlockNotHandled
        currentState = block.getState()
        if block.wantsLine(line):
            # If we're in the block, we returned Handled, because, as long as
            # we are inside the block, we want to keep ourselves as a handler.
            handled = self.BlockHandled
            if currentState == block.InsideBlockState:
                didMatch, updated = block.processLine(line)
                if didMatch:
                    if self._handleLine(block):
                        handled = self.BlockShouldExit
                # If we didn't match, we may have hit the end of the block. So
                # check to see if we match the closing expression. If
                # successful, isFinished will call reset on the block.
                if not didMatch and block.isFinished(line):
                    handled = self.BlockNotHandled

        return handled

    def parse(self):
        lineData = self._getNextLine()
        while lineData:
            if isinstance(self, StreamContext):
                self.bufferLine(lineData)

            handled = self.BlockNotHandled
            currentMatchers = self.currentMatchers.copy()
            for currentMatcher in currentMatchers:
                handled = self._processBlock(lineData, currentMatcher)
                if handled == self.BlockNotHandled:
                    self.currentMatchers.remove(currentMatcher)

            if handled == self.BlockNotHandled or not self.isCooperative:
                for block in self.blockMatchers:
                    if block not in self.currentMatchers:
                        handled = self._processBlock(lineData, block)
                        if handled == self.BlockHandled:
                            self.currentMatchers.append(block)
                            if not self.isCooperative:
                                break

            if self.outputStream is not None:
                self.outputStream.write(lineData)
            lineData = self._getNextLine()

        self.completeParsing()


class FileStreamParser(StreamParser):
    def __init__(self, path, process=True):
        super(FileStreamParser, self).__init__()
        self.path = path
        self.inputStream = open(self.path, "r", encoding='utf-8')
        if process:
            self.newPath = path + ".new"
            self.outputStream = open(self.newPath, "w")

    def _completeParsing(self):
        self.inputStream.close()
        if self.outputStream:
            self.outputStream.close()


class UrlStreamParser(StreamParser, StreamContext):
    def __init__(self, host, isSecure=False):
        # Multiple base classes, so we need to call both init's explicitly
        # super(UrlStreamParser, self).__init__()
        StreamParser.__init__(self)
        StreamContext.__init__(self)
        self.host = host
        self.isSecure = isSecure
        # default type. What we use if we can't get it from the HTTP headers
        if isSecure:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.verify_mode = ssl.CERT_NONE
            self.client = http.client.HTTPSConnection(host, context=context)
        else:
            self.client = http.client.HTTPConnection(host)
        self.isValid = False

    # Sets the URL path for the parse() function. We've set the host in the
    # constructor, so this resets everything, and reads from the specified
    # URL from that hose.
    # Returns: (HTTP status, Reason). 200 means, okay.
    # Be sure to check the return code for this. The URL may not be valid, or
    # it may have moved
    def setPath(self, path):
        self.reset()
        # Since we're a StreamContext
        self.contextReset()
        try:
            self.client.request('GET', path)
        except ConnectionRefusedError:
            extra = ''
            if self.isSecure:
                extra = '(over SSL)'
            print('Failed to connect to %s %s' % (self.host, extra))
        resp = None
        try:
            resp = self.client.getresponse()
        except http.client.ResponseNotReady as error:
            if resp is not None:
                resp.read()
            # Some errors aren't entirely ERROR-worthy
            print('ERROR: Response not ready for %s: %s' % (path, error))
            return (error, None)

        self.status = resp.status
        self.reason = resp.reason
        if self.status != 200:
            if self.status == 301 or self.status == 302:
                # Read the rest of the body
                resp.read()
                return (self.status, resp.getheader('Location', None))
            else:
                return (self.status, resp.reason)

        # Get the encoding
        contentType = resp.getheader('Content-Type')
        if contentType is not None:
            ctParts = contentType.split(';')
            if len(ctParts) == 2:
                charTypeParts = ctParts[1].split('=')
                if len(charTypeParts) == 2:
                    encoding = charTypeParts[1]
                    self.encoding = encoding

        if resp is not None:
            self.isValid = True
        self.inputStream = resp
        return (self.status, None)

    def _completeParsing(self):
        # Read the rest of the data
        if not self.forceConnectionClose:
            self.inputStream.read()
        self.inputStream.close()
        self.closeContext()


class BufferStreamParser(StreamParser):
    # mirrors some of the StreamContext variables, since this is kind of the
    # analog to it, but we don't derive from it.

    #    def __init__(self, lines):
    #        super(BufferStreamParser, self).__init__()
    #        self._currentLineNumber = 0;
    #        self._lines = lines

    # parses a section of a StreamContext, starting from startLine, ending
    # (whether or not we're successful)  at endLine.
    def __init__(self, streamContext, startLine, endLine=None):
        super(BufferStreamParser, self).__init__()
        self._currentLineNumber = startLine
        self._lines = streamContext._lines
        self._endLine = endLine

    def _completeParsing(self):
        # just in memory, so nothing to read off the disk or socket
        pass

    def _getNextLine(self):
        if self._endLine is None or \
           self._currentLineNumber <= self._endLine:
            if self._currentLineNumber < len(self._lines):
                line = self._lines[self._currentLineNumber]
                self._currentLineNumber += 1
                return line
        return None
