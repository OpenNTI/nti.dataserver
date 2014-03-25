#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Partial support for the amsopn package

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Command

class DeclareMathOperator(Command):
	args = '* {name:str}{arguments:str} '

