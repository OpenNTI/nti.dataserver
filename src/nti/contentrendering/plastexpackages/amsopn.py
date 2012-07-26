#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from plasTeX import Command

# SAJ: Partial support for the amsopn package.

class DeclareMathOperator(Command):
	args = '* {name:str}{arguments:str} '

