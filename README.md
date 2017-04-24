# BlockEx

[![Build Status](https://travis-ci.org/shigmas/BlockEx.svg?branch=master)](https://travis-ci.org/shigmas/BlockEx)


A regular expression parsing library in Python.

# The problem
You have a regular expression in a stream or a file, and it is not uniquely
identifiable by itself.

For example, if you are looking in an Xcode project file, and you are looking for
the VALID_ARCHS line:
```
    VALID_ARCHS[sdk=*]" = "arm64 armv7 armv7s x86_64";
```

This is easy enough to find with a simple regular expression. But, if we only want
 that line in the Debug configuration, you need at least one more regular
 expression to find the opening blocks of containing the block (JSON in this
 case):

```
    939CB4A41C31ED1100720F6E /* Debug */ = {
        isa = XCBuildConfiguration;
            buildSettings = {
```

In addition, we'd also like to know when the block ends, so we don't change the
Release configuration's VALID_ARCHS if the Debug configuration does not contain a
line matching that regular expression:
```
    };
    name = Debug;
```

So, we can define some regular expressions to say when to start looking for the
VALID_ARCHS's regular expression, and a regular expression to signal when to stop looking for it. (Currently, only one stopping regular expression is allowed.)

# API
There are two public facing objects:
## StreamParser
StreamParser has two subclasses, FileStreamParser and UrlStreamParser, or you can
write your own. Your Parser must override _handleLine, which takes a 'matcher' is
parameter. The matcher is an instance of BlockBase or subclass that you pass into
the StreamParser init. (Using a delegate would be a good idea, but there are some
other features that are more needed.)
## BlockBase
The BlockBase's init takes list of opening regular expressions, a PatternMatchex,
which is the 'main' regular expression, and an ending regular expression, which
denotes the end of the block.

# Example
Using the example of the Xcode project file, we'll create a subclass of BlockBase
FileStreamParser and a subclass of BlockBase:
```
class XcodeBlockBase(BlockEx.BlockBase):
    def __init__(self):
        regex = r'\s+VALID_ARCHS\[sdk=\*\] = \"(\w+\s*)+\";'

        matchex = BlockEx.PatternMatchex(blockRegex = regex)
        openers = [r'\s+\w+\s+/\* Debug \*/ = \{',
                   r'\s+isa = XCBuildConfiguration',
                   r'\s+buildSettings = \{']

        super(XcodeBlockBase, self).__init__(openingRegexStrings = openers,
                                             blockMatchex = matchex,
                                             endingRegexString = r'\s+\};')

class XcodeParser(BlockEx.FileStreamParser):

    def __init__(self, filePath):
        super(XcodeParser, self).__init__(filePath)
        self.setMatchers([XcodeBlockBase()])
        
    def _handleLine(self, matcher):
        patternMatchex = matcher.blockMatchex

        if patternMatchex.groups is None:
            return
        print('number of groups: %d' % len(patternMatchex.groups))
        for group in patternMatchex.groups:
            print('match: %s' % group)

        matcher.blockMatchex.groups = None

def main(args):
    if len(args) != 2:
        return -1

    parser = XcodeParser(args[1])
    parser.parse()

if __name__ == '__main__':
    main(sys.argv)
```
