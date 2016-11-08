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

from zope.intid.interfaces import IIntIds

from zope.mimetype.interfaces import IContentTypeAware

from z3c.schema.email.field import isValidMailAddress

from nti.containers.containers import CaseInsensitiveLastModifiedBTreeContainer

from nti.coremetadata.interfaces import SYSTEM_USER_NAME

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationsContainer

from nti.invitations.utils import get_random_invitation_code

from nti.property.property import alias

from nti.schema.eqhash import EqHash

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

@WithRepr
@EqHash('code')
@interface.implementer(IInvitation, IAttributeAnnotatable, IContentTypeAware)
class Invitation(PersistentCreatedModDateTrackingObject,
				 SchemaConfigured):

	createDirectFieldProperties(IInvitation)

	__parent__ = None
	__name__ = alias('code')

	username = alias('receiver')
	inviter = creator = alias('sender')
	expirationTime = alias('expiryTime')
		
	parameters = {} # IContentTypeAware

	mimeType = mime_type = u"application/vnd.nextthought.invitation"

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
		PersistentCreatedModDateTrackingObject.__init__(self)

	@readproperty
	def sender(self):
		return SYSTEM_USER_NAME

	def is_email(self):
		return bool(self.receiver and isValidMailAddress(self.receiver))
	isEmail = is_email

	def is_expired(self, now=None):
		expirationTime = self.expiryTime
		now = time.time() if not now else now
		return bool(expirationTime and expirationTime <= now)
	isExpired = is_expired
	
	def is_accepted(self):
		return self.accepted
	isAccepted = is_accepted

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

@interface.implementer(IInvitationsContainer, IAttributeAnnotatable)
class InvitationsContainer(CaseInsensitiveLastModifiedBTreeContainer,
						   Contained):
	
	def add(self, invitation):
		code = invitation.code
		if not code:
			code = get_random_invitation_code()
			while code in self:
				code = get_random_invitation_code()
			invitation.code = code
		self[code] = invitation
	registerInvitation = append = add
	
	def remove(self, invitation):
		code = getattr(invitation, 'code', invitation)
		if code in self:
			del self[code]
			return True
		return False
	removeInvitation = remove
	
	def getInvitationByCode(self, code):
		return self.get(code)

def install_invitations_container(site_manager_container, intids=None):
	lsm = site_manager_container.getSiteManager()
	intids = lsm.getUtility(IIntIds) if intids is None else intids
	registry = lsm.queryUtility(IInvitationsContainer)
	if registry is None:
		registry = InvitationsContainer()
		registry.__parent__ = site_manager_container
		registry.__name__ = '++etc++invitations-container'
		intids.register(registry)
		lsm.registerUtility(registry, provided=IInvitationsContainer)
	return registry
