#!/usr/bin/env python3

from Parser import FileStreamParser
from BlockMatchex import PatternMatchex
from BlockBase import BlockBase

import json

import unittest


class ZBlock(BlockBase):
    def __init__(self):
        regex = r'.*;window\.zara\.dataLayer = (\{.*\});window\.zara\.viewPayload = window'
        matchex = PatternMatchex(blockRegex=regex)
        openers = [r'\s+<li><a href="http://www\.zara\.com/us/en/contact',
                   r'\s+</ul>',
                   r'\s+</li>', ]
        endingRegex = r'\s+\(function\(\)\{'
        super(ZBlock, self).__init__(openingRegexStrings=openers,
                                     blockMatchex=matchex,
                                     endingRegexString=endingRegex)


class ZParser(FileStreamParser):
    def _handleLine(self, matcher):
        matches = matcher.blockMatchex.matchStrings
        rawMatch = matches[0]
        jDict = json.loads(rawMatch)
        print('keys: %s' % jDict.keys())
        self.jsonData = jDict


class TestParser(unittest.TestCase):

    def setUp(self):
        self.matchIndices = []
        self.closers = []
        self.matcher = None

    # This is the index (int) of the match), and the match object
    def onOpeningMatch(self, index, match):
        self.matchIndices.append(index)

    def onRegexMatch(self, match):
        print('regex match')

    def onClosingMatch(self, match):
        self.closers.append(match)

    def ntestFindRegexes(self):
        ''' Finds the regexes in a block with 3 pre regexes, and 1 closing.
        '''
        zParser = ZParser('tests/zara.test', process=False)
        zBlock = ZBlock()
        zBlock.delegate = self
        zParser.blockMatchers = [zBlock, ]
        zParser.parse()

        self.assertEqual(len(self.matchIndices), 3,
                         'Num pre regex matches does not match')
        self.assertEqual(len(self.closers), 1,
                         'Num closers does not match')
        self.assertIsNotNone(zParser.jsonData,
                             'Main Matches not matched')

    def ntestCoopRegexFind(self):
        ''' Tests two identical regexes that should succeed together
        '''
        zParser = ZParser('tests/zara.test', process=False)
        zBlock1 = ZBlock()
        zBlock2 = ZBlock()
        zBlock1.delegate = self
        zBlock2.delegate = self
        zParser.blockMatchers = [zBlock1, zBlock2]
        zParser.parse()

        self.assertEqual(len(self.matchIndices), 6,
                         'Num pre regex matches does not match')
        self.assertEqual(len(self.closers), 2,
                         'Num closers does not match')
        self.assertIsNotNone(zParser.jsonData,
                             'Main Matches not matched')

    def testNonCoopRegexFind(self):
        ''' Tests two identical regexes that should succeed together
        '''
        zParser = ZParser('tests/zara.test', process=False)
        zParser.isCooperative = False
        zBlock1 = ZBlock()
        zBlock2 = ZBlock()
        zBlock1.delegate = self
        zBlock2.delegate = self
        zParser.blockMatchers = [zBlock1, zBlock2]
        zParser.parse()

        # Unlike the coop one, only one block should have gotten results.
        self.assertEqual(len(self.matchIndices), 3,
                         'Num pre regex matches does not match')
        self.assertEqual(len(self.closers), 1,
                         'Num closers does not match')
        self.assertIsNotNone(zParser.jsonData,
                             'Main Matches not matched')


if __name__ == '__main__':
    unittest.main()
