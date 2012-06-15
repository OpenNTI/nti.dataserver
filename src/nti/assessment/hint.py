#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals


from zope import interface
from zope import component

from nti.assessment import interfaces
from ._util import TrivialValuedMixin

from persistent import Persistent

@interface.implementer(interfaces.IQHint)
class QHint(Persistent):
	"""
	Base class for hints.
	"""

@interface.implementer(interfaces.IQTextHint)
class QTextHint(TrivialValuedMixin,QHint):
	"""
	A text hint.
	"""
