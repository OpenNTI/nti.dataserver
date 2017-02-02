#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import isodate
from urllib import unquote
from datetime import datetime

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.component.hooks import site as current_site

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users import all_usernames
from nti.app.users import username_search

from nti.app.users.utils import generate_mail_verification_pair

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import EmailAddressInvalid

from nti.dataserver.users.utils import reindex_email_verification

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.site.hostpolicy import get_all_host_sites

from nti.zodb.containers import bit64_int_to_time

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_config(name='GetUserBlacklist')
@view_config(name='get_user_black_list')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='GET',
               context=IDataserverFolder)
class GetUserBlacklistView(AbstractAuthenticatedView):

    def __call__(self):
        user_blacklist = component.getUtility(IUserBlacklistedStorage)

        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = vals = {}

        count = 0
        for key, val in list(user_blacklist):
            val = datetime.fromtimestamp(bit64_int_to_time(val))
            vals[key] = isodate.datetime_isoformat(val)
            count += 1
        result[TOTAL] = result[ITEM_COUNT] = count
        return result


@view_config(name='ResetUserBlacklist')
@view_config(name='reset_user_black_list')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='POST',
               context=IDataserverFolder)
class ResetUserBlacklistView(AbstractAuthenticatedView):

    def __call__(self):
        user_blacklist = component.getUtility(IUserBlacklistedStorage)
        user_blacklist.clear()
        return hexc.HTTPNoContent()


@view_config(name='RemoveFromUserBlacklist')
@view_config(name='remove_from_user_black_list')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='POST',
               context=IDataserverFolder)
class RemoveFromUserBlacklistView(AbstractAuthenticatedView,
                                  ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        usernames = values.get('user') \
            or values.get('users') \
            or values.get('username') \
            or values.get('usernames')
        if isinstance(usernames, six.string_types):
            usernames = usernames.split(",")
        if not usernames:
            raise hexc.HTTPUnprocessableEntity(_("Must specify a username."))

        result = LocatedExternalDict()
        items = result[ITEMS] = []
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context

        user_blacklist = component.getUtility(IUserBlacklistedStorage)
        for username in set(usernames):
            if username and user_blacklist.remove_blacklist_for_user(username):
                items.append(username)

        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='GetEmailVerificationToken')
@view_config(name='get_email_verification_token')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IDataserverFolder,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class GetEmailVerificationTokenView(AbstractAuthenticatedView):

    def __call__(self):
        values = CaseInsensitiveDict(self.request.params)
        username = values.get('username') or values.get('user')
        if not username:
            raise hexc.HTTPUnprocessableEntity(_("Must specify a username."))

        user = User.get_user(username)
        if user is None or not IUser.providedBy(user):
            raise hexc.HTTPUnprocessableEntity(_("User not found."))

        profile = IUserProfile(user)
        email = values.get('email') or profile.email
        if not email:
            raise hexc.HTTPUnprocessableEntity(
                _("Email address not provided."))

        signature, token = generate_mail_verification_pair(user, email)
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result['Signature'] = signature
        result['Token'] = token
        return result


@view_config(name='ForceUserEmailVerification')
@view_config(name='force_user_email_verification')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IDataserverFolder,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class ForceEmailVerificationView(AbstractAuthenticatedView,
                                 ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        username = values.get('username') or values.get('user')
        if not username:
            raise hexc.HTTPUnprocessableEntity(_("Must specify a username."))

        user = User.get_user(username)
        if user is None or not IUser.providedBy(user):
            raise hexc.HTTPUnprocessableEntity(_("User not found."))

        profile = IUserProfile(user)
        email = values.get('email') or profile.email
        if not email:
            raise hexc.HTTPUnprocessableEntity(
                _("Email address not provided."))
        else:
            try:
                checkEmailAddress(email)
            except EmailAddressInvalid:
                raise hexc.HTTPUnprocessableEntity(_("Invalid email address."))

        profile.email = email
        profile.email_verified = True
        verified = reindex_email_verification(user)
        assert verified

        return hexc.HTTPNoContent()


@view_config(name='RemoveUser')
@view_config(name='remove_user')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='POST',
               context=IDataserverFolder)
class RemoveUserView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        username = values.get('username') or values.get('user')
        if not username:
            raise hexc.HTTPUnprocessableEntity(_("Must specify a username."))

        user = User.get_user(username)
        if user is None or not IUser.providedBy(user):
            raise hexc.HTTPUnprocessableEntity(_("User not found."))

        User.delete_user(username)
        return hexc.HTTPNoContent()


@view_config(name='GetUserGhostContainers')
@view_config(name='get_user_ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               permission=nauth.ACT_NTI_ADMIN)
class GetUserGhostContainersView(AbstractAuthenticatedView):

    exclude_containers = (u'Devices', u'FriendsLists', u'', u'Blog', ROOT)

    def _find_object(self, name):
        if not is_valid_ntiid_string(name):
            return None

        # try current site
        result = find_object_with_ntiid(name)
        if result is not None:
            return

        # look in other sites
        for site in get_all_host_sites():
            with current_site(site):
                result = find_object_with_ntiid(name)
                if result is not None:
                    return result
        return None

    def _check_users_containers(self, usernames=()):
        for username in usernames or ():
            user = User.get_user(username)
            if user is None or not IUser.providedBy(user):
                continue
            usermap = {}
            method = getattr(user, 'getAllContainers', lambda: ())
            for name in method():
                if name in self.exclude_containers:
                    continue

                target = self._find_object(name)
                if target is None:
                    container = user.getContainer(name)
                    usermap[name] = len(container) if container else 0
            if usermap:
                yield user.username, usermap

    def __call__(self):
        values = CaseInsensitiveDict(self.request.params)
        term = values.get('term') or values.get('search')
        usernames = values.get('usernames') or values.get('username')
        if term:
            usernames = username_search(unquote(term))
        elif isinstance(usernames, six.string_types):
            usernames = set(unquote(usernames).split(","))
        else:
            usernames = all_usernames()

        result = LocatedExternalDict()
        items = result[ITEMS] = {}
        for username, rmap in self._check_users_containers(usernames):
            items[username] = rmap
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result
