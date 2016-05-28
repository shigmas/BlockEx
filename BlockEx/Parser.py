import http.client

import ssl
import re
import types

class StreamParser(object):

    def __init__(self):
        self.blockMatchers = []
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
        pass
    
    def _handleLine(self, matcher):
        # for concrete subclasses that want data from the line (versus the ones
        # that only want to read the file in and write it out), we have this hook
        # to parse out the line.
        return False

    def parse(self):
        line = self.inputStream.readline()
        while line:
            # if line is a byte-type, we need to convert it to unicode. But,
            # ATM, I want to know what types.Bytes is.
            lineData = str(line, encoding=self.encoding)
            if self.currentBlockMatcher is not None and \
               self.currentBlockMatcher.wantsLine(lineData):
                line = self.currentBlockMatcher.processLine(lineData)
                shouldExit = self._handleLine(self.currentBlockMatcher)
                if shouldExit is not None and shouldExit:
                    self.completeParsing()
                    return
            else: # go through all the blocks to see
                newMatcher = False
                for matcher in self.blockMatchers:
                    if matcher.wantsLine(lineData):
                        self.currentBlockMatcher = matcher
                        newMatcher = True
                        line = matcher.processLine(lineData)
                        shouldExit = self._handleLine(self.currentBlockMatcher)
                        if shouldExit is not None and shouldExit:
                            self.completeParsing()
                            return
                        if matcher.matchexFound() and not matcher.allowNext():
                            break
                if not newMatcher:
                    currentBlockMatcher = None
            if self.outputStream is not None:
                self.outputStream.write(line)
            line = self.inputStream.readline()

class FileStreamParser(StreamParser):
    def __init__(self, path, process=True):
        super(FileStreamParser, self).__init__()
        self.path = path
        self.inputStream = file(self.path,"r")
        if process:
            self.newPath = path + ".new"
            self.outputStream = file(self.newPath,"w")

    def completeParsing(self):
        self.inputStream.close()
        if self.outputStream:
            self.outputStream.close()

class UrlStreamParser(StreamParser):
    def __init__(self, host, isSecure=False):
        super(UrlStreamParser, self).__init__()
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
        try:
            resp = self.client.getresponse()
        except http.client.ResponseNotReady as error:
            print('ERROR: Response not ready for %s: %s' % (path, error))
            return
        self.status = resp.status
        self.reason = resp.reason
        if self.status != 200:
            print('ERROR status for %s: %s' % (path, self.status))
            return

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
        
    def completeParsing(self):
        # Read the rest of the data 
        if not self.forceConnectionClose:
            self.inputStream.read()
        self.inputStream.close()
