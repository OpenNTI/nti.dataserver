#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.cachedescriptors.property import readproperty

from zope.intid.interfaces import IIntIds

from zope.container.contained import Contained

from zope.mimetype.interfaces import IContentTypeAware

from z3c.schema.email.field import isValidMailAddress

from nti.common.property import alias

from nti.coremetadata.interfaces import SYSTEM_USER_NAME

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.invitations.interfaces import IInvitation

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import EqHash

@WithRepr
@EqHash('code')
@interface.implementer(IInvitation, IAttributeAnnotatable, IContentTypeAware)
class Invitation(PersistentCreatedModDateTrackingObject,
				 SchemaConfigured,
				 Contained):

	createDirectFieldProperties(IInvitation)

	inviter = alias('sender')
	username = alias('receiver')

	parameters = {} # IContentTypeAware

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
		PersistentCreatedModDateTrackingObject.__init__(self)

	@readproperty
	def code(self):
		intids = component.queryUtility(IIntIds)
		result = intids.queryId(self) if intids is not None else None
		return result

	@readproperty
	def sender(self):
		return SYSTEM_USER_NAME

	def is_email(self):
		return self.receiver and isValidMailAddress(self.receiver)
	isEmail = is_email

	def is_expired(self):
		expirationTime = self.expirationTime
		return expirationTime and expirationTime <= time.time()
	isExpired = is_expired
	
	def __lt__(self, other):
		try:
			return (self.code, self.createdTime) < (self.code, self.createdTime)
		except AttributeError:  # pragma: no cover
			return NotImplemented

	def __gt__(self, other):
		try:
			return (self.code, self.createdTime) > (self.code, self.createdTime)
		except AttributeError:  # pragma: no cover
			return NotImplemented
