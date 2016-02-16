import re

class BlockBase(object):
    DefaultBlockState = 0       # Not in the block
    OpeningBlockState = 1       # Block is possibly open
    InsideBlockState  = 2       # We're inside the block
    ClosingBlockState = 3       # Not in the block

    # Construct a BlockBase.
    # startingRegexes: sequence of regexes that signifies the start of the block
    # blockRegex: the line we are looking for in the regex
    # endingRegex: the regex that signifies the end of the block
    def __init__(self, openingRegexStrings, blockMatchex, endingRegexString):
        self.currentState = self.DefaultBlockState
        # save this for bookkeeping
        self.openingRegexStrings = openingRegexStrings
        self.openingRegexes = []
        for reString in openingRegexStrings:
            self.openingRegexes.append(re.compile(reString))
        if len(self.openingRegexes) == 0:
            # this skips the default and opening states. If there's no closing
            # regex, we'll never hit that either
            self.resetState = self.InsideBlockState
        else:
            self.resetState = self.DefaultBlockState
        self.blockMatchex = blockMatchex
        if endingRegexString is not None:
            self.endingRegex = re.compile(endingRegexString)
            self.endState = self.ClosingBlockState
        else:
            self.endingRegex = None
            self.endState = self.InsideBlockState

        self.reset()

    def reset(self):

        self.currentState = self.resetState
        self.openingRegexesIndex = 0
        self.updatedLine = None
        self.blockMatchex.reset()
        
    def getCurrentState(self):
        return self.currentState

    def getUpdatedLine(self):
        return self.updatedLine

    # Returns true if this matcher will allow the next to process. This is true
    # if we don't have an opening block, since, otherwise, we'd never allow
    # other matchers to get a chance.
    def allowNext(self):
        return len(self.openingRegexes) == 0

    def matchexFound(self):
        return self.blockMatchex.matchFound

    def _matchOpening(self, line):
        match = self.openingRegexes[self.openingRegexesIndex].match(line)
        if match:
            if len(self.openingRegexes) == self.openingRegexesIndex + 1:
                self.currentState = self.InsideBlockState
            else:
                self.currentState = self.OpeningBlockState
                self.openingRegexesIndex = self.openingRegexesIndex + 1

            return True
        else:
            return self.DefaultBlockState

    # This is a little complex, but...
    # If the line makes us (or keeps us) the active matcher, return true.
    def wantsLine(self, line):
        if self.currentState == self.DefaultBlockState:
            # make sure the opening index is reset
            self.openingRegexesIndex = 0
            if self._matchOpening(line) == self.DefaultBlockState:
                return False
            else:
                return True
        elif self.currentState == self.OpeningBlockState:
            if self._matchOpening(line) == self.DefaultBlockState:
                return False
            else:
                return True
        elif self.currentState == self.InsideBlockState:
            # If we don't have an opening line, then we see if the main match
            # to see if we want
            if (self.resetState == self.InsideBlockState) and \
               not self.blockMatchex.blockRegex.match(line):
                return False
            # Inside the block, the state doesn't change unless we hit the
            # end of the block
            if self.endingRegex and self.endingRegex.match(line):
                self.currentState = self.endState
                return True
            return True
        elif self.currentState == self.ClosingBlockState:
            # If we've reached the closing, reset so subsequent matchers
            # (including ourselves) can have a chance at processing
            self.currentState = self.DefaultBlockState
            return False

    # Unless we are inside of a block, we'll return the line as it
    # is.  If we're inside the block, we hand it to the blockMatchex. That will
    # do any number of things, depending on the matchex.
    def processLine(self, line):
        if self.currentState == self.DefaultBlockState or \
           self.currentState == self.OpeningBlockState:
            return line
        elif self.currentState == self.InsideBlockState:
            # This might be the exact same line
            updated = self.blockMatchex.matchLine(line)
            return updated
        elif self.currentState == self.ClosingBlockState:
            if not self.blockMatchex.matchFound:
                # We didn't find a match for the block that we were looking
                # for, so we create a new line.
                completeLine = self.blockMatchex.getCompleteLine()
                if completeLine is not None:
                    updated = '%s%s' % (completeLine,line)
                    return updated
                else:
                    return line
            else:
                return line
            self.currentState = self.DefaultBlockState
        else:
            print('unknown: %s' % line)
        return line

class BuildSettingsBlock(BlockBase):
    def __init__(self):
        opening = [r'(\s+)\w+\s\/\*\sDebug\s\*\/\s=\s{.*',
                   r'\s+isa\s=\s\w+;',
                   r'\s+buildSettings\s=\s{']
        matchString = r'\s+VALID_ARCHS\s+=\s+"(.+)";'
        indentString = r'(\s+).+;'
        ending = '\s+};'
        matchex = BlockMatchex(indentString, matchString, 'VALID_ARCHS',
                               'x86_64',['arm64','armv7','armv7s'])

        super(BuildSettingsBlock,self).__init__(opening, matchex, ending)

class PbxParse(object):
    def __init__(self, path):
        self.path = path
        self.newPath = path + ".new"
        self.blockMatchers = [BuildSettingsBlock()]
        self.currentBlockMatcher = None

    def parse(self):
        iF = file(self.path,"r")
        oF = file(self.path + ".new","w")
        line = iF.readline()
        while line:
            if self.currentBlockMatcher is not None and \
               self.currentBlockMatcher.wantsLine(line):
                line = self.currentBlockMatcher.processLine(line)
            else: # go through all the blocks to see 
                for matcher in self.blockMatchers:
                    if matcher.wantsLine(line):
                        self.currentBlockMatcher = matcher
                        line = matcher.processLine(line)
                        break

            oF.write(line)
            line = iF.readline()
        iF.close()
        oF.close()

def main(args, stdout, environ):
#    f = '~/src/tree/futomen/core/FFKit/FFKit.xcodeproj/project.pbxproj'
    f = args[1]
    key = 'VALID_ARCHS'
    x86 = 'x86_64'
    parser = PbxParse(f)
    parser.parse()
    print('all done')

if __name__ == '__main__':
    main(sys.argv, sys.stdout, os.environ)
