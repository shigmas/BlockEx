import re, types

# A Regular expression and what to do with it.
class BlockMatchex(object):
    # Params:
    # o indentRegex: regex to capture the indentation so that we can apply the
    #   same indentation pattern to the lines that we add
    # o blockRegex: pattern for the line we are hoping to modify
    def __init__(self, blockRegex):
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
    groups = []
    def _processLine(self, matchObj, line):
        self.groups = matchObj.groups()
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
        self.blockRegex = re.compile(blockRegex)
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
