#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.interfaces import IContainer

class ISAMLIDPUserInfoBindings(IContainer):
	"""
	A container-like object storing ISAMLIDPUserInfo (provider-specific ID info)
	by the IDP entityid that provided the assertion
	"""

class ISAMLProviderUserInfo(interface.Interface):
	"""
	Provider specific user information to be stored on user
	"""
