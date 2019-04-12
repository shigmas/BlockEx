#!/usr/bin/env python3

from BlockEx.Parser import FileStreamParser
from BlockEx.BlockMatchex import DictMatchex
from BlockEx.BlockBase import BlockBase

import unittest


# Some test code for pbxproject files.
class BuildSettingsBlock(BlockBase):
    def __init__(self):
        opening = [r'(\s+)\w+\s\/\*\sDebug\s\*\/\s=\s{.*',
                   r'\s+isa\s=\s\w+;',
                   r'\s+buildSettings\s=\s{']
        matchString = r'\s+VALID_ARCHS\s+=\s+"(.+)";'
        indentString = r'(\s+).+;'
        ending = r'\s+};'
        matchex = DictMatchex(indentString, matchString, 'VALID_ARCHS',
                              'x86_64', ['arm64', 'armv7', 'armv7s'])

        super(BuildSettingsBlock, self).__init__(opening, matchex, ending)


class TestPbxParser(unittest.TestCase):

    def testParsePbx(self):
        parser = FileStreamParser('tests/project.pbxproj',
                                  process=True)
        parser.parse()
        print('all done')


if __name__ == '__main__':
    unittest.main()
