import re

class BlockBase(object):
    OpeningBlockState = 0       # Block is possibly open
    InsideBlockState  = 1       # We're inside the block
    ClosingBlockState = 2       # Not in the block

    # Construct a BlockBase.
    # startingRegexes: sequence of regexes that signifies the start of the
    # block
    # blockRegex: the line we are looking for in the regex
    # endingRegex: the regex that signifies the end of the block
    def __init__(self, openingRegexStrings, blockMatchex, endingRegexString):
        self.openingRegexes = []
        for reString in openingRegexStrings:
            if len(reString) > 0:
                self.openingRegexes.append(re.compile(reString))
        self.blockMatchex = blockMatchex
        if endingRegexString is not None and len(endingRegexString) > 0:
            self.endingRegex = re.compile(endingRegexString)
        else:
            self.endingRegex = None
        self.reset()
        self.delegate = None

    def reset(self):
        if self.openingRegexes is not None:
            self._matchIndex = 0
        else:
            self._matchIndex = -1

        self.blockMatchex.reset()

    def getState(self):
        # Similar to GetRegex, but a little simpler.
        if self._matchIndex < 0:
            return self.InsideBlockState
        numOpening = len(self.openingRegexes)
        if self._matchIndex < numOpening:
            return self.OpeningBlockState
        elif self._matchIndex == numOpening:
            return self.InsideBlockState
        elif self._matchIndex == numOpening + 1 and \
             self.endingRegex is not None:
            return self.ClosingBlockState
        else:
            # This is an error. Our index stepped past our regexes
            raise 'Index (%d) is greater than our regexes' % self._matchIndex

    def _getOpeningRegex(self):
        if self._matchIndex < 0:
            return None
        # Uses the current index to see which match we're currently testing
        numOpening = len(self.openingRegexes)
        if self._matchIndex < numOpening:
            return self.openingRegexes[self._matchIndex]
        else:
            # This is an error. Our index stepped past our regexes
            raise 'Index (%d) is greater than our regexes' % self._matchIndex

    # Return True if we want to set or keep this BlockBase to be the current
    # or to continue processing with this block
    def wantsLine(self, line):
        state = self.getState()
        if state == self.OpeningBlockState:
            # If we have opening regexes, check the match. If successful,
            # increment and return true. Else, reset. If xthere are no opening
            # regexes, state is already InsideBlockState
            regex = self._getOpeningRegex()
            match = regex.match(line)

            if match is None:
                self.reset()
                return False
            else:
                if self.delegate:
                    self.delegate.onOpeningMatch(self._matchIndex, match)
                self._matchIndex += 1
                return True
        elif state == self.InsideBlockState:
            # There's only one possible match inside the block, but there might
            # be other lines inside that don't match, so we 'want' the line
            # until we hit the closing. For now, we return True. ProcessLine()
            # check to see if we should process the line by checking if we
            # match and passing it to the matchex.
            return True
        else:
            # This function should only be handling theOpening and Inside
            # states!
            print('WARNING: Unhandled states in WantsLine()!!!')
            return False

    # Callback for processLine(), which is called whenever we are inside the
    # block, whether or not it matches the regular expression. We ignore any
    # return values, so this is really just for debugging
    def _processLine(self, line):
        pass

    # Unless we are inside of a block, we'll return the line as it
    # is.  If we're inside the block, we hand it to the blockMatchex. That will
    # do any number of things, depending on the matchex.
    # Returns:
    # 1. a boolean if we successfully processed the line (whatever that may
    #    be,
    # 2. The updated line, which may be modified, or the same line, if we are
    #    just looking for the match.
    def processLine(self, line):
        self._processLine(line)
        state = self.getState()
        didMatch = False
        if state != self.InsideBlockState:
            print('WARNING: Calling processLine when not inside the block')
            return didMatch, line
        else:
            match = self.blockMatchex.testMatch(line)
            if match is not None:
                didMatch = True
                if self.delegate is not None:
                    self.delegate.onRegexMatch(match)
                # updated may or may not be the same as line. True tells us
                # that we had a match.
                updated = self.blockMatchex.matchLine(line, match)
                return didMatch, updated
            else:
                return didMatch, line

    def isFinished(self, line):
        state = self.getState()
        result = False
        if state == self.InsideBlockState:
            # We want to see if we've finished processing, which is indicated
            # by any one of the following conditions
            # 1. We hit the closing regex, if there is a closing regex
            # 2. If there is no closing regex, if the matchex had a match.
            #
            # The result of this rule is that we can continue sending lines
            # to the matchex if we provide a closing regex. Otherwise, hitting
            # the matchex regex means we're done processing.
            if self.endingRegex is not None:
                closingMatch = self.endingRegex.match(line)
                if closingMatch is not None:
                    if self.delegate is not None:
                        self.delegate.onClosingMatch(closingMatch)
                    # Maybe let the Parser call this?
                    self._finishProcessing(line)
                    result = True
                    self.reset()
            elif self.blockMatchex.matchFound:
                # Maybe let the Parser call this?
                self._finishProcessing(line)
                result = True
                self.reset()

        return result

    def _finishProcessing(self, line):
        # I'm not exactly sure what I was doing here. We need to
        # return a new line if we are "processing" e.g. modifying the
        # line.

        # We didn't find a match for the block that we were looking
        # for, so we create a new line.
        completeLine = self.blockMatchex.getCompleteLine()
        if completeLine is not None:
            updated = '%s%s' % (completeLine, line)
            return updated
        else:
            return line
