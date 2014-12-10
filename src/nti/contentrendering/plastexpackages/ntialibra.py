#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alibra macros

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Base
from plasTeX.Packages import graphicx

from ._util import LocalContentMixin
from .ntilatexmacros import ntidirectionsblock

# pylint
Base = Base
LocalContentMixin = LocalContentMixin

class rightpic(graphicx.includegraphics):
	packageName = 'ntialibra'
	blockType = True

class putright(rightpic):
	pass

class alibradirectionsblock(ntidirectionsblock):
	pass

class alibraimage(graphicx.includegraphics):
	packageName = 'ntialibra'
	blockType = True
	args = '* [ options:dict ] file:str:source description'
