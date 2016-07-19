#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.security.interfaces import IPrincipal

from nti.common.property import Lazy

from nti.contentfile.interfaces import IContentBaseFile

from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_CONTENT_ADMIN

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import ALL_PERMISSIONS

@component.adapter(IContentBaseFile)
@interface.implementer(IACLProvider)
class ContentBaseFileACLProvider(object):
	"""
	Provides the basic ACL for a content folder.
	"""

	def __init__(self, context):
		self.context = context

	@property
	def __parent__(self):
		# See comments in nti.dataserver.authorization_acl:has_permission
		return self.context.__parent__

	@Lazy
	def __aces__(self):
		aces = [ace_allowing(ROLE_ADMIN, ALL_PERMISSIONS, self),
				ace_allowing(ROLE_CONTENT_ADMIN, ALL_PERMISSIONS, type(self))]
		creator = IPrincipal(self.context.creator, None)
		if creator is not None:
			aces.append(ace_allowing(creator, ALL_PERMISSIONS, self))
		return aces
		
	@Lazy
	def __acl__(self):
		result = acl_from_aces(self.__aces__)
		return result
