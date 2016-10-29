import re, types

# A Regular expression and what to do with it.
class BlockMatchex(object):
    # Params:
    # o indentRegex: regex to capture the indentation so that we can apply the
    #   same indentation pattern to the lines that we add
    # o blockRegex: pattern for the line we are hoping to modify
    def __init__(self, blockRegex, flags =  None):
        self._flags = flags
        # calls the property setter
        self.blockRegexString = blockRegex
        if self._flags is not None:
            self.blockRegex = re.compile(blockRegex, self._flags)
        else:
            self.blockRegex = re.compile(blockRegex)
        self.matchFound = False
        self.previousLine = None

    def reset(self):
        self.matchFound = False
        self.previousLine = None
        
    # Takes the regex match object, and line 
    def _processLine(self, matchObj, line):
        return line

    # If you want to create a line through the Matchex, do it here.
    def getCompleteLine(self):
        return None

    # Just tests the match without parsing it (since sometimes we have a
    # secondary match).
    def testMatch(self, line):
        return self._match(line)

    def _match(self, line):
        return self.blockRegex.match(line)

    def matchLine(self, line):
        self.previousLine = line
        match = self.blockRegex.match(line)
        if match:
            self.matchFound = True
            return self._processLine(match, line)
        return line

# On a match on the regular expression, gets the groups marked in the regular
# expression.
# XXX - We should also just have a boolean in case we just want to know if there
# was a match and we don't care about what was in the match
class PatternMatchex(BlockMatchex):
    def __init__(self, blockRegex, flags =  None):
        super(PatternMatchex, self).__init__(blockRegex, flags)
        self.matchStrings = []
        self.groups = []

    def _processLine(self, matchObj, line):
        matchStrings = []
        groups = []
        numGroups = len(matchObj.groups())
        if numGroups > 0:
            for i in (1, len(matchObj.groups())):
                matchStr = matchObj.group(i)
                print
                matchStrings.append(matchStr)
                #print('pair: %s, %d - %d' % (matchStr, matchObj.start(i),
                #                             matchObj.end(i)))
                groups.append((matchStr, (matchObj.start(i),matchObj.end(i))))
            self.groups = groups
            self.matchStrings = matchStrings

        return line

# If we just want to find all the occurences
class FindAllMatchex(BlockMatchex):
    def __init__(self, blockRegex, findAll=True, flags =  None):
        super(FindAllMatchex, self).__init__(blockRegex, flags)
        self.groups = []

    def _match(self, line):
        if len(self.blockRegex.findall(line)) == 0:
            return None
        else:
            return True

    def matchLine(self, line):
        self.previousLine = line
        matches = self.blockRegex.findall(line)
        if matches:
            self.matchFound = True
            self.groups = matches
            return self._processLine(matches, line)
        return line

# We find all the patterns that match the expression (like FindAllMatchex), and
# then create a new expression to find the locations of all those matches
# (like PatternMatchex).
class MultiPatternMatchex(FindAllMatchex):
    def __init__(self, blockRegex, flags =  None):
        super(MultiPatternMatchex, self).__init__(blockRegex, flags)
        self._secondaryMatchString = None
        self.groups = []
        self.matchStrings = []

    def _buildMatchString(self, numMatches):
        regex = '.*'
        for i in range(0, numMatches):
            regex += self.blockRegexString + '.*'

        return regex

    # FindAll's matchLine calls us.
    def _processLine(self, matchObj, line):
        numMatches = len(matchObj)
        self._patternRegexString = self._buildMatchString(numMatches)
        patternMatches = re.match(self._patternRegexString,line)
        numGroups = 0
        if patternMatches is not None:
            numGroups = len(patternMatches.groups())
        if numGroups > 0:
            groups = []
            matchStrings = []
            for i in range(1, numGroups):
                matchStr = patternMatches.group(i)
                matchStrings.append(matchStr)
                #print('pair: %s, %d - %d' % (matchStr, patternMatches.start(i),
                #                             patternMatches.end(i)))
                groups.append((matchStr, (patternMatches.start(i),
                                          patternMatches.end(i))))
            self.groups = groups
            self.matchStrings = matchStrings

        return line

# Matchex to find a key in a string and check the values. If it doesn't contain
# all the values we need, we add them. If the line doesn't exist at all, we
# create the line with the necessary values.
class DictMatchex(BlockMatchex):
    # Params:
    # o indentRegex: regex to capture the indentation so that we can apply the
    #   same indentation pattern to the lines, in case we need to create the
    #   line from scratch
    # o blockRegex: pattern for the line we are hoping to modify
    # o key: key that we are looking for
    # o value: The value that want to add
    # o expectedValues: The values that we expect to already be there
    # Params:
    # o indentRegex: regex to capture the indentation so that we can apply the
    #   same indentation pattern to the lines that we add
    # o blockRegex: pattern for the line we are hoping to modify
    def __init__(self, indentRegex, blockRegex, key, value, expectedValues):
        super(DictMatchex, self).__init__(blockRegex)
        self.key = key
        self.value = value
        # could be a string or list type.
        self.expectedValues = expectedValues

    def _getValueString(self):
        if type(self.expectedValues) is types.ListType:
            newVals = self.expectedValues[:]
            newVals.append(self.value)
            return ' '.join(newVals)

    def _processLine(self, matchObj, line):
        oldVals = matchObj.group(1)
        vals = oldVals.split()
        hasVal = False
        for val in vals:
            if val == self.value:
                hasVal = True
                break
        if not hasVal:
            vals.append(self.value)
            newVals = ' '.join(vals)
            return line.replace(oldVals,newVals)

        return line

    def getCompleteLine(self):
        prevMatch = self.indentRegex.match(self.previousLine)
        prevIndent = prevMatch.group(1)
        # For bool values, we don't want to quote them.  But, since we're only
        # doing this for one type of value so far, let's not compliate things.
        return '%s%s = \"%s\";\n' % (prevIndent, self.key, self._getValueString())
