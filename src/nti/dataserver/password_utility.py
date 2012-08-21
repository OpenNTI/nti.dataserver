#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains a :mod:`z3c.password.password` utility
designed for persistence and storing in ZODB.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

import persistent
import z3c.password.password

from nti.dataserver import interfaces as nti_interfaces

@interface.implementer(nti_interfaces.IZContained)
class HighSecurityPasswordUtility(persistent.Persistent,z3c.password.password.HighSecurityPasswordUtility):
	"""
	A password policy that is designed for persistent storage in the ZODB.
	"""

	__name__ = None
	__parent__ = None
