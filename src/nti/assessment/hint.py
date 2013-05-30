#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from nti.assessment import interfaces
from ._util import TrivialValuedMixin

from persistent import Persistent

@interface.implementer(interfaces.IQHint)
class QHint(Persistent):
	"""
	Base class for hints.
	"""

@interface.implementer(interfaces.IQTextHint)
class QTextHint(TrivialValuedMixin, QHint):
	"""
	A text hint.
	"""


@interface.implementer(interfaces.IQHTMLHint)
class QHTMLHint(TrivialValuedMixin, QHint):
	"""
	A text hint.
	"""
