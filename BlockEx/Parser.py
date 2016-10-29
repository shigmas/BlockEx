import http.client

import ssl
import re
import types


class StreamContext(object):
    def __init__(self):
        self._lines = []
        #self._outputStream = open('webout',"w", encoding='utf-8')
        
    def bufferLine(self, line):
        self._lines.append(line)
        self._outputStream.write(line)

    def getCurrentLineNumber(self):
        return len(self._lines) -1

    def getLineAt(self, number):
        if number < len(self._lines):
            return self._lines[number]
        else:
            print('%s beyond index' % number )
            return None

    def closeContext(self):
        self._outputStream.close()

class StreamParser(object):
    def __init__(self):
        self.blockMatchers = []
        self.cooperative = True
        self.reset()

    def reset(self):
        for matcher in self.blockMatchers:
            matcher.reset()
        self.currentBlockMatcher = None
        self.encoding = 'utf-8'
        self.inputStream = None
        self.outputStream = None
        self.status = 0
        self.reason = None
        self.forceConnectionClose = False
        
    def setMatchers(self, matchers):
        self.blockMatchers = matchers

    def completeParsing(self):
        self._completeParsing()
        if isinstance(self, StreamContext):
            self.bufferLine(self._getNextLine())


    # Subclasses implement this function. This gets called when the BlockBase
    # "wants" the line, not just on a match. _handleLine can know if it is called
    # on a match if there is actually match data to process.
    def _handleLine(self, matcher):
        # for concrete subclasses that want data from the line (versus the ones
        # that only want to read the file in and write it out), we have this hook
        # to parse out the line.
        return False

    def _getNextLine(self):
        line = self.inputStream.readline()
        # if line is a byte-type, we need to convert it to unicode. I believe
        # readline was returning bytes (Python 2.x?), but if it returns
        # a string, we don't need convert again.
        if isinstance(line,str):
            return line
        else:
            return str(line, encoding=self.encoding)
    
    def parse(self):
        lineData = self._getNextLine()
        while lineData:
            if isinstance(self, StreamContext):
                self.bufferLine(lineData)

            if self.currentBlockMatcher is not None and \
               self.currentBlockMatcher.wantsLine(lineData) and \
               not self.cooperative:
                # Only do this case if we're non-cooperative. Othewise, we
                # can let the main clause handle everything.
                if self.currentBlockMatcher.getsLine(line):
                    line = self.currentBlockMatcher.processLine(lineData)
                    shouldExit = self._handleLine(self.currentBlockMatcher)
                    if shouldExit is not None and shouldExit:
                        self.completeParsing()
                        return
            else:
                newMatcher = False
                for matcher in self.blockMatchers:
                    if matcher.wantsLine(lineData):
                        # Save the currentBlockMatcher for later (if non-coop),
                        # but use the matcher since it's shorter
                        self.currentBlockMatcher = matcher
                        if self.currentBlockMatcher.getsLine(lineData):
                            line = matcher.processLine(lineData)
                            shouldExit = self._handleLine(matcher)
                            if matcher.matchexFound() and not self.cooperative:
                                break
                if not newMatcher:
                    currentBlockMatcher = None
            if self.outputStream is not None:
                self.outputStream.write(line)
            lineData = self._getNextLine()

class FileStreamParser(StreamParser):
    def __init__(self, path, process=True):
        super(FileStreamParser, self).__init__()
        self.path = path
        self.inputStream = open(self.path,"r", encoding='utf-8')
        if process:
            self.newPath = path + ".new"
            self.outputStream = open(self.newPath,"w")

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

        # default type. What we use if we can't get it from the HTTP headers
        if isSecure:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.verify_mode = ssl.CERT_NONE
            self.client = http.client.HTTPSConnection(host, context=context)
        else:
            self.client = http.client.HTTPConnection(host)
              
    def setPath(self, path):
        self.reset()
        req = self.client.request('GET', path)
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
                return (self.status, resp.getheader('Location',None))
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
        self.inputStream = resp
        return (self.status, None)
        
    def _completeParsing(self):
        # Read the rest of the data 
        if not self.forceConnectionClose:
            self.inputStream.read()
        self.inputStream.close()

class BufferStreamParser(StreamParser):
    # mirrors some of the StreamContext variables, since this is kind of the
    # analog to it, but we don't derive from it.
#    def __init__(self, lines):
#        super(BufferStreamParser, self).__init__()
#        self._currentLineNumber = 0;
#        self._lines = lines

    # parses a section of a StreamContext, starting from startLine, ending
    # (whether or not we're successful)  at endLine.
    def __init__(self, streamContext, startLine, endLine = None):
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

