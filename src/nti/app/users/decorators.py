#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IHiddenMembership

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link

from nti.traversal.traversal import find_interface

from .import REQUEST_EMAIL_VERFICATION_VIEW
from .import VERIFY_USER_EMAIL_WITH_TOKEN_VIEW

LINKS = StandardExternalFields.LINKS

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _UserEmailVerificationLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		profile = IUserProfile(context, None)
		result = bool(	self._is_authenticated and \
						profile is not None and \
						not profile.email_verified )
		return result

	def _do_decorate_external(self, context, result):
		_links = result.setdefault(LINKS, [])
		link = Link(context, rel="RequestEmailVerification",
					elements=(REQUEST_EMAIL_VERFICATION_VIEW,))
		_links.append(link)
		
		ds2 = find_interface(context, IDataserverFolder)
		link = Link(ds2, rel="VerifyEmailWithToken", method='POST',
					elements=('@@' + VERIFY_USER_EMAIL_WITH_TOKEN_VIEW,))
		_links.append(link)

@component.adapter(ICommunity)
@interface.implementer(IExternalMappingDecorator)
class _CommunityLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		result = bool(self._is_authenticated)
		return result

	def _do_decorate_external(self, context, result):
		_links = result.setdefault(LINKS, [])
		in_community = self.remoteUser in context
		if context.joinable:
			if not in_community:
				link = Link(context, rel="join")
			else:
				link = Link(context, rel="leave")
			_links.append(link)
		
		if context.public:
			link = Link(context, rel="members")
			_links.append(link)

		if self.remoteUser in IHiddenMembership(context, None) or ():
			link = Link(context, rel="unhide")
		else:
			link = Link(context, rel="hide")
		_links.append(link)
