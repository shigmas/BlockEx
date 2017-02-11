#!/usr/bin/env python3

from Parser import FileStreamParser
from BlockMatchex import PatternMatchex
from BlockBase import BlockBase

import re

import unittest


class OneLineBlock(BlockBase):
    def __init__(self):
        regex = r'this\sis\sa.*line'
        matchex = PatternMatchex(blockRegex=regex,
                                 flags=re.IGNORECASE)
        super(OneLineBlock, self).__init__(openingRegexStrings=[],
                                           blockMatchex=matchex,
                                           endingRegexString=None)


class OneLineParser(FileStreamParser):

    def _handleLine(self, matcher):
        if not hasattr(self, 'numMatches'):
            setattr(self, 'numMatches', 0)
        self.numMatches += 1


class TestParser(unittest.TestCase):
    def testOneLine(self):
        olParser = OneLineParser('tests/easy.test', process=False)
        olParser.isCooperative = False
        olParser.blockMatchers = [OneLineBlock(), ]

        olParser.parse()
        self.assertEqual(2, olParser.numMatches, 'Wrong number of matches')


if __name__ == '__main__':
    unittest.main()
