#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.cachedescriptors.property import readproperty

from zope.container.contained import Contained

from zope.mimetype.interfaces import IContentTypeAware

from z3c.schema.email.field import isValidMailAddress

from nti.common.property import alias

from nti.common.random import generate_random_hex_string

from nti.containers.containers import CaseInsensitiveLastModifiedBTreeContainer

from nti.coremetadata.interfaces import SYSTEM_USER_NAME

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitations

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
	expirationTime = alias('expiryTime')

	parameters = {} # IContentTypeAware

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
		PersistentCreatedModDateTrackingObject.__init__(self)

	@readproperty
	def sender(self):
		return SYSTEM_USER_NAME

	def is_email(self):
		return self.receiver and isValidMailAddress(self.receiver)
	isEmail = is_email

	def is_expired(self):
		expirationTime = self.expiryTime
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

@interface.implementer(IInvitations, IAttributeAnnotatable)
class InvitationsContainer(CaseInsensitiveLastModifiedBTreeContainer):
	
	def add(self, invitation):
		code = invitation.code
		if not code:
			code = generate_random_hex_string()
			while code in self:
				code = generate_random_hex_string()
		self[code] = invitation
	registerInvitation = append = add
	
	def remove(self, invitation):
		code = getattr(invitation, 'code', invitation)
		del self[code]
	removeInvitation = remove
	
	getInvitationByCode = CaseInsensitiveLastModifiedBTreeContainer.__getitem__
