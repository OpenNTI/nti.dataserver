#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import base64

from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator
from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.app.users import VIEW_USER_TOKENS
from nti.app.users import REL_MY_MEMBERSHIP
from nti.app.users import SUGGESTED_CONTACTS
from nti.app.users import VIEW_GRANT_USER_ACCESS
from nti.app.users import VIEW_RESTRICT_USER_ACCESS
from nti.app.users import REQUEST_EMAIL_VERFICATION_VIEW
from nti.app.users import VERIFY_USER_EMAIL_WITH_TOKEN_VIEW

from nti.app.users import MessageFactory as _

from nti.app.users.utils import get_user_creation_sitename

from nti.appserver.pyramid_authorization import has_permission

from nti.appserver.workspaces.interfaces import ICatalogWorkspaceLinkProvider

from nti.coremetadata.interfaces import IDeactivatedUser
from nti.coremetadata.interfaces import IDeactivatedCommunity
from nti.coremetadata.interfaces import IDeleteLockedCommunity

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_DELETE
from nti.dataserver.authorization import ACT_UPDATE

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin
from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import ISiteAdminUtility
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.interfaces import IAuthToken
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IHiddenMembership
from nti.dataserver.users.interfaces import IDisallowMembersLink
from nti.dataserver.users.interfaces import IDisallowActivityLink
from nti.dataserver.users.interfaces import IDisallowHiddenMembership
from nti.dataserver.users.interfaces import IDisallowSuggestedContacts

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.identifiers.utils import get_external_identifiers

from nti.links.links import Link

from nti.traversal.traversal import find_interface

LINKS = StandardExternalFields.LINKS

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _UserEmailVerificationLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        profile = IUserProfile(context, None)
        result = bool(    self._is_authenticated
                      and self.remoteUser == context
                      and profile is not None
                      and not profile.email_verified
                      and not is_admin(context))
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

    def _predicate(self, unused_context, unused_result):
        result = self._is_authenticated
        return result

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context, rel="memberships", elements=('@@memberships',))
        _links.append(link)


@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _UserAdminInfoDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Decorate external identifiers for the user or administrators.
    """

    def _predicate(self, user_context, unused_result):
        if not self._is_authenticated:
            return False
        result = is_admin(self.remoteUser) or self.remoteUser == user_context
        if not result and is_site_admin(self.remoteUser):
            site_admin_utility = component.getUtility(ISiteAdminUtility)
            result = site_admin_utility.can_administer_user(self.remoteUser,
                                                            user_context)
        return result

    def _do_decorate_external(self, context, result):
        external_ids = get_external_identifiers(context)
        if external_ids:
            result['external_ids'] = external_ids
        result['lastSeenTime'] = context.lastSeenTime
        result['lastLoginTime'] = context.lastLoginTime
        result['CreationSite'] = get_user_creation_sitename(context)
        if self.remoteUser != context:
            _links = result.setdefault(LINKS, [])
            if IDeactivatedUser.providedBy(context):
                result['Deactivated'] = True
                link = Link(context, elements=('@@Restore',), rel="Restore")
            else:
                link = Link(context, elements=('@@Deactivate',), rel="Deactivate")
            _links.append(link)


@component.adapter(ICommunity)
@interface.implementer(IExternalMappingDecorator)
class _CommunityLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, unused_context, unused_result):
        result = bool(self._is_authenticated)
        return result

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        in_community = self.remoteUser in context
        is_admin_user = is_admin_or_site_admin(self.remoteUser)
        user_can_update = has_permission(ACT_UPDATE, context)
        result['RemoteIsMember'] = in_community
        result['NumberOfMembers'] = context.number_of_members()
        result['DeleteLocked'] = IDeleteLockedCommunity.providedBy(context)
        if      (    context.joinable \
                 and context.auto_subscribe is None) \
            or user_can_update:
            if not in_community:
                link = Link(context, elements=('@@join',), rel="join")
            else:
                link = Link(context, elements=('@@leave',), rel="leave")
            _links.append(link)

        if      not IDisallowMembersLink.providedBy(context) \
            and (context.public or in_community or is_admin_user):
            link = Link(context, elements=('members',), rel="members")
            _links.append(link)

        if is_admin_user:
            link = Link(context,
                        elements=('members',),
                        rel="AddMembers",
                        method="POST")
            _links.append(link)
            link = Link(context,
                        elements=('members', '@@bulk_remove'),
                        rel="RemoveMembers",
                        method='POST')
            _links.append(link)

        if in_community and not IDisallowHiddenMembership.providedBy(context):
            if self.remoteUser in IHiddenMembership(context, None) or ():
                link = Link(context, elements=('@@unhide',), rel="unhide")
            else:
                link = Link(context, elements=('@@hide',), rel="hide")
            _links.append(link)

        if not IDisallowActivityLink.providedBy(context):
            link = Link(context,
                        elements=('@@Activity',),
                        rel="Activity",
                        title=_("All Activity"))
            _links.append(link)

        if      not IDeactivatedCommunity.providedBy(context) \
            and not IDeleteLockedCommunity.providedBy(context) \
            and has_permission(ACT_DELETE, context):
            link = Link(context,
                        rel="delete",
                        method='DELETE')
            _links.append(link)

        if      IDeactivatedCommunity.providedBy(context) \
            and user_can_update:
            link = Link(context,
                        rel="restore",
                        elements=('@@Restore',),
                        method='POST')
            _links.append(link)

        if user_can_update:
            link = Link(context,
                        rel="edit",
                        method='PUT')
            _links.append(link)


@interface.implementer(IExternalMappingDecorator)
@component.adapter(IDynamicSharingTargetFriendsList, IRequest)
class _DFLGetMembershipLinkProvider(AbstractTwoStateViewLinkDecorator):

    true_view = REL_MY_MEMBERSHIP

    def link_predicate(self, context, unused_current_username):
        user = self.remoteUser
        result = user is not None and user in context and not context.Locked
        return result


@component.adapter(IDynamicSharingTargetFriendsList)
@interface.implementer(IExternalMappingDecorator)
class _DFLLinksDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        result = bool(self._is_authenticated
                      and (   self.remoteUser in context
                           or self.remoteUser == context.creator))
        return result

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context, rel="Activity", elements=('Activity',))
        _links.append(link)


@component.adapter(IUser, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _UserSuggestedContactsLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context,
                    rel=SUGGESTED_CONTACTS,
                    elements=(SUGGESTED_CONTACTS,))
        _links.append(link)


@component.adapter(ICommunity, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _CommunitySuggestedContactsLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        # Should we check for public here? It's false by default.
        result = bool(self._is_authenticated
                      and not IDisallowSuggestedContacts.providedBy(context)
                      or (   self.remoteUser in context
                          or self.remoteUser == context.creator))
        return result

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context,
                    rel=SUGGESTED_CONTACTS,
                    elements=(SUGGESTED_CONTACTS,))
        _links.append(link)


@component.adapter(IDynamicSharingTargetFriendsList, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _DFLSuggestedContactsLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        result = bool(self._is_authenticated
                      and (   self.remoteUser in context
                           or self.remoteUser == context.creator))
        return result

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context,
                    rel=SUGGESTED_CONTACTS,
                    elements=(SUGGESTED_CONTACTS,))
        _links.append(link)


@component.adapter(IUser)
@interface.implementer(ICatalogWorkspaceLinkProvider)
class _CatalogWorkspaceAdminLinkDecorator(object):

    def __init__(self, user):
        self.user = user

    def links(self, catalog_workspace):
        if is_admin_or_site_admin(self.user):
            result = []
            ds2 = find_interface(catalog_workspace, IDataserverFolder)
            for rel in (VIEW_GRANT_USER_ACCESS, VIEW_RESTRICT_USER_ACCESS):
                link = Link(ds2,
                            rel=rel,
                            elements=(rel,),
                            method='POST')
                result.append(link)
            return result
        return ()


@component.adapter(IUser, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _UserTokensLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        return bool(self._is_authenticated and self.remoteUser == context)

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context, rel=VIEW_USER_TOKENS, elements=(VIEW_USER_TOKENS,))
        _links.append(link)


@component.adapter(IAuthToken)
@interface.implementer(IExternalMappingDecorator)
class _AuthTokenEncodedTokenDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        result =    self._is_authenticated \
                and has_permission(ACT_READ, context)
        return result

    def _do_decorate_external(self, context, result):
        encoded_token = base64.b64encode('%s:%s' % (self.remoteUser.username, context.token))
        result['EncodedToken'] = encoded_token
