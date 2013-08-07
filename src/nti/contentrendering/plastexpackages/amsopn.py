#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from plasTeX import Command

# SAJ: Partial support for the amsopn package.

class DeclareMathOperator(Command):
	args = '* {name:str}{arguments:str} '

