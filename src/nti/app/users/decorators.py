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

from pyramid.interfaces import IRequest

from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator
from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.app.users import REL_MY_MEMBERSHIP
from nti.app.users import SUGGESTED_CONTACTS
from nti.app.users import REQUEST_EMAIL_VERFICATION_VIEW
from nti.app.users import VERIFY_USER_EMAIL_WITH_TOKEN_VIEW

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IHiddenMembership
from nti.dataserver.users.interfaces import IDisallowMembersLink
from nti.dataserver.users.interfaces import IDisallowActivityLink
from nti.dataserver.users.interfaces import IDisallowHiddenMembership
from nti.dataserver.users.interfaces import IDisallowSuggestedContacts

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import SingletonDecorator

from nti.links.links import Link

from nti.traversal.traversal import find_interface

LINKS = StandardExternalFields.LINKS

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _UserEmailVerificationLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		profile = IUserProfile(context, None)
		result = bool(	  self._is_authenticated 
					  and self.remoteUser == context
					  and profile is not None
					  and not profile.email_verified)
		return result

	def _do_decorate_external(self, context, result):
		_links = result.setdefault(LINKS, [])
		link = Link(context, rel="RequestEmailVerification",
					elements=('@@' + REQUEST_EMAIL_VERFICATION_VIEW,))
		_links.append(link)

		ds2 = find_interface(context, IDataserverFolder)
		link = Link(ds2, rel="VerifyEmailWithToken", method='POST',
					elements=('@@' + VERIFY_USER_EMAIL_WITH_TOKEN_VIEW,))
		_links.append(link)

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _UserMembershipsLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		result = self._is_authenticated
		return result

	def _do_decorate_external(self, context, result):
		_links = result.setdefault(LINKS, [])
		link = Link(context, rel="memberships", elements=('@@memberships',))
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
				link = Link(context, elements=('@@join',), rel="join")
			else:
				link = Link(context, elements=('@@leave',), rel="leave")
			_links.append(link)

		if not IDisallowMembersLink.providedBy(context) and (context.public or in_community):
			link = Link(context, elements=('@@members',), rel="members")
			_links.append(link)

		if in_community and not IDisallowHiddenMembership.providedBy(context):
			if self.remoteUser in IHiddenMembership(context, None) or ():
				link = Link(context, elements=('@@unhide',), rel="unhide")
			else:
				link = Link(context, elements=('@@hide',), rel="hide")
			_links.append(link)

		if not IDisallowActivityLink.providedBy(context):
			link = Link(context, elements=('@@Activity',), rel="Activity")
			_links.append(link)

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IDynamicSharingTargetFriendsList, IRequest)
class _DFLGetMembershipLinkProvider(AbstractTwoStateViewLinkDecorator):

	true_view = REL_MY_MEMBERSHIP

	def link_predicate(self, context, current_username):
		user = self.remoteUser
		result = user is not None and user in context and not context.Locked
		return result

@component.adapter(IDynamicSharingTargetFriendsList)
@interface.implementer(IExternalMappingDecorator)
class _DFLLinksDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		result = bool(self._is_authenticated 
					  and (	   self.remoteUser in context 
					  		or self.remoteUser == context.creator))
		return result

	def _do_decorate_external(self, context, result):
		_links = result.setdefault(LINKS, [])
		link = Link(context, rel="Activity", elements=('Activity',))
		_links.append(link)

@component.adapter(IDynamicSharingTargetFriendsList)
@interface.implementer(IExternalObjectDecorator)
class _DFLEditLinkRemoverDecorator(object):
	"""
	Remove the edit link if the DFL is locked

	:Note The order in which decorators are called is completely
	undefined. The only reason this happens to work now
	is the distinction between IExternalObjectDecorator
	and IExternalMappingDecorator; if any of the registrations
	change this will break.
	"""

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, context, external):
		links = external.get(LINKS, ())
		if context.Locked:
			for idx, link in enumerate(tuple(links)):  # mutating
				if link.get('rel') == 'edit':
					links.pop(idx)
					break
		if not links and LINKS in external:
			del external[LINKS]

@component.adapter(IUser, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _UserSuggestedContactsLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _do_decorate_external(self, context, result):
		_links = result.setdefault(LINKS, [])
		link = Link(context, rel=SUGGESTED_CONTACTS, elements=(SUGGESTED_CONTACTS,))
		_links.append(link)

@component.adapter(ICommunity, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _CommunitySuggestedContactsLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		# Should we check for public here? It's false by default.
		result = bool(self._is_authenticated \
					  and not IDisallowSuggestedContacts.providedBy(context) \
					  or (	 self.remoteUser in context \
						  or self.remoteUser == context.creator))
		return result

	def _do_decorate_external(self, context, result):
		_links = result.setdefault(LINKS, [])
		link = Link(context, rel=SUGGESTED_CONTACTS, elements=(SUGGESTED_CONTACTS,))
		_links.append(link)

@component.adapter(IDynamicSharingTargetFriendsList, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _DFLSuggestedContactsLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		result = bool(self._is_authenticated \
					  and (		self.remoteUser in context \
					  		or	self.remoteUser == context.creator))
		return result

	def _do_decorate_external(self, context, result):
		_links = result.setdefault(LINKS, [])
		link = Link(context, rel=SUGGESTED_CONTACTS, elements=(SUGGESTED_CONTACTS,))
		_links.append(link)
