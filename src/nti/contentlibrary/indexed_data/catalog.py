#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface

from nti.zope_catalog.index import AttributeValueIndex as ValueIndex

class ValidatingSiteName(object):

	__slots__ = (b'site',)

	def __init__(self, obj, default=None):
		folder = find_interface(obj, IHostPolicyFolder, strict=False)
		if folder is not None:
			self.site = folder.__name__

	def __reduce__(self):
		raise TypeError()

class SiteIndex(ValueIndex):
	default_field_name = 'site'
	default_interface = ValidatingSiteName
