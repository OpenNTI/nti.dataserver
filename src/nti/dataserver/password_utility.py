#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains a :mod:`z3c.password.password` utility
designed for persistence and storing in ZODB.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from z3c.password.password import HighSecurityPasswordUtility

from persistent import Persistent

from .interfaces import IZContained

@interface.implementer(IZContained)
class HighSecurityPasswordUtility(Persistent, HighSecurityPasswordUtility):
	"""
	A password policy that is designed for persistent storage in the ZODB.
	"""
	__name__ = None
	__parent__ = None
