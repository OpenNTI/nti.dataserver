#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six
import isodate
from datetime import datetime
from six.moves import urllib_parse

from requests.structures import CaseInsensitiveDict

from zope import component
from zope import interface

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from zope.event import notify

from zope.intid.interfaces import IIntIds

from zope.security.management import endInteraction
from zope.security.management import restoreInteraction

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users import VIEW_USER_UPSERT
from nti.app.users import VIEW_GRANT_USER_ACCESS
from nti.app.users import VIEW_RESTRICT_USER_ACCESS

from nti.app.users.utils import set_user_creation_site
from nti.app.users.utils import generate_mail_verification_pair

from nti.app.users.views import username_search
from nti.app.users.views import raise_http_error

from nti.app.users.views.view_mixins import AbstractUpdateView
from nti.app.users.views.view_mixins import UserUpsertViewMixin
from nti.app.users.views.view_mixins import GrantAccessViewMixin
from nti.app.users.views.view_mixins import RemoveAccessViewMixin

from nti.appserver.interfaces import INamedLinkView

from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users.index import get_entity_catalog
from nti.dataserver.users.index import add_catalog_filters

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import EmailAddressInvalid

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import reindex_email_verification

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.identifiers.utils import get_user_for_external_id

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.site.hostpolicy import get_all_host_sites, get_host_site

from nti.zodb.containers import bit64_int_to_time

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(name='GetUserBlacklist')
@view_config(name='get_user_black_list')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='GET',
               context=IDataserverFolder)
class GetUserBlacklistView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        user_blacklist = component.getUtility(IUserBlacklistedStorage)
        for key, val in list(user_blacklist):
            val = datetime.fromtimestamp(bit64_int_to_time(val))
            items[key] = isodate.datetime_isoformat(val)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
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
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
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
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        user = User.get_user(username)
        if user is None or not IUser.providedBy(user):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'User not found.'),
                             },
                             None)
        profile = IUserProfile(user)
        email = values.get('email') or profile.email
        if not email:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Email address not provided.'),
                             },
                             None)
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
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        user = User.get_user(username)
        if not IUser.providedBy(user):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'User not found.'),
                             },
                             None)
        profile = IUserProfile(user)
        email = values.get('email') or profile.email
        if not email:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Email address not provided.'),
                             },
                             None)
        else:
            try:
                checkEmailAddress(email)
            except EmailAddressInvalid:
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid email address.'),
                                 },
                                 None)
        profile.email = email
        profile.email_verified = True
        verified = reindex_email_verification(user)
        assert verified

        return hexc.HTTPNoContent()


@view_config(name='SetUserCreationSite')
@view_config(name='set_user_creation_site')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IDataserverFolder,
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN)
class SetUserCreationSiteView(AbstractAuthenticatedView,
                              ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        username = values.get('username') or values.get('user')
        if not username:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        user = User.get_user(username)
        if not IUser.providedBy(user):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'User not found.'),
                             },
                             None)
        site = values.get('site') or getattr(getSite(), '__name__', None)
        if site != 'dataserver2':
            site = get_host_site(site, True) if site else None
            if site is None:
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 {
                                     'message': _(u'Invalid site.'),
                                 },
                                 None)

        set_user_creation_site(user, site)
        return hexc.HTTPNoContent()


@view_config(name='RemoveUser')
@view_config(name='remove_user')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_NTI_ADMIN,
               request_method='POST',
               context=IDataserverFolder)
class RemoveUserView(AbstractAuthenticatedView,
                     ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        values = CaseInsensitiveDict(self.readInput())
        username = values.get('username') or values.get('user')
        if not username:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        user = User.get_user(username)
        if user is None or not IUser.providedBy(user):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'User not found.'),
                             },
                             None)
        endInteraction()
        try:
            User.delete_user(username)
        finally:
            restoreInteraction()
        return hexc.HTTPNoContent()


@view_config(name='GhostContainers')
@view_config(name='ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               context=IUser,
               renderer='rest',
               request_method='GET',
               permission=nauth.ACT_READ)
class UserGhostContainersView(AbstractAuthenticatedView):

    exclude_containers = (u'Devices', u'FriendsLists', u'', u'Blog', ROOT)

    def _check_access(self):
        result = self.remoteUser == self.context \
              or nauth.is_admin(self.remoteUser)
        if not result:
            raise hexc.HTTPForbidden()

    def _find_object(self, name):
        if not is_valid_ntiid_string(name):
            return None
        # try current site
        result = find_object_with_ntiid(name)
        if result is not None:
            return result
        # look in other sites
        for site in get_all_host_sites():
            with current_site(site):
                result = find_object_with_ntiid(name)
                if result is not None:
                    return result
        return None

    def _all_exclude(self, user):
        blog = IPersonalBlog(user, None)
        ntiid = (blog.NTIID,) if blog is not None else ()
        return ntiid + self.exclude_containers

    def _find_user_containers(self, user):
        usermap = {}
        to_exclude = self._all_exclude(user)
        for name in user.getAllContainers():
            if name in to_exclude:
                continue
            target = self._find_object(name)
            if target is None:
                container = user.getContainer(name)
                usermap[name] = len(container) if container else 0
        return usermap

    def _delete_containers(self, user, items):
        for containerId in items or ():
            user.deleteContainer(containerId)

    def __call__(self):
        self._check_access()
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = self._find_user_containers(self.context)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='RemoveGhostContainers')
@view_config(name='remove_ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               context=IUser,
               renderer='rest',
               request_method='POST',
               permission=nauth.ACT_READ)
class RemoveUserGhostContainersView(UserGhostContainersView):

    def __call__(self):
        result = super(RemoveUserGhostContainersView, self).__call__()
        self._delete_containers(self.context, result[ITEMS].keys())
        return result


@view_config(name='GhostContainers')
@view_config(name='ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class GetGhostContainersView(UserGhostContainersView):

    def _check_users_containers(self, usernames=()):
        for username in usernames or ():
            user = User.get_user(username)
            if not IUser.providedBy(user):
                continue
            usermap = self._find_user_containers(user)
            yield user, usermap

    def _parse_usernames(self, values):
        term = values.get('term') or values.get('search')
        usernames = values.get('usernames') or values.get('username')
        # pylint: disable=too-many-function-args
        if term:
            usernames = username_search(urllib_parse.unquote(term))
        elif isinstance(usernames, six.string_types):
            usernames = set(urllib_parse.unquote(usernames).split(","))
        else:
            usernames = ()
        return usernames

    def __call__(self):
        values = CaseInsensitiveDict(self.request.params)
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = {}
        usernames = self._parse_usernames(values)
        for user, rmap in self._check_users_containers(usernames):
            items[user.username] = rmap
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='RemoveGhostContainers')
@view_config(name='remove_ghost_containers')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class RemoveGhostContainersView(GetGhostContainersView,
                                ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        if self.request.body:
            result = super(RemoveGhostContainersView, self).readInput(value)
        else:
            result = {}
        return CaseInsensitiveDict(result)

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = {}
        usernames = self._parse_usernames(self.readInput())
        for user, rmap in self._check_users_containers(usernames):
            items[user.username] = rmap
            self._delete_containers(user, rmap.keys())
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name='RebuildEntityCatalog')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class RebuildEntityCatalogView(AbstractAuthenticatedView):

    def __call__(self):
        intids = component.getUtility(IIntIds)
        # clear indexes
        catalog = get_entity_catalog()
        for index in catalog.values():
            index.clear()
        # filters need to be added
        add_catalog_filters(catalog, catalog.family)
        # reindex
        count = 0
        dataserver = component.getUtility(IDataserver)
        users_folder = IShardLayout(dataserver).users_folder
        # pylint: disable=no-member
        for obj in users_folder.values():
            doc_id = intids.queryId(obj)
            if doc_id is None:
                continue
            count += 1
            catalog.index_doc(doc_id, obj)
        result = LocatedExternalDict()
        result[ITEM_COUNT] = result[TOTAL] = count
        return result


@view_config(name='LinkUserExternalIdentity')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IUser,
               permission=nauth.ACT_NTI_ADMIN)
class LinkUserExternalIdentityView(AbstractUpdateView):
    """
    An admin view to link the contextual user with external identifiers. This
    information will be associated to the current site.
    """

    def _predicate(self):
        if     not self._external_type \
            or not self._external_id:
            raise_http_error(self.request,
                             _(u"Require external_type and external_id to link user."),
                            u'CannotLinkUserExternalIdentityError')

    def __call__(self):
        external_user = get_user_for_external_id(self._external_type,
                                                 self._external_id)
        # pylint: disable=no-member
        if      external_user \
            and external_user != self.context:
            logger.warn("""Mapping user to existing external identity (%s)
                           (existing=%s) (external_type=%s) (external_id=%s)""",
                        self.context.username, external_user.username,
                        self._external_type,
                        self._external_id)
            raise_http_error(self.request,
                             _(u"Multiple users mapped to this external identity."),
                             u'DuplicateUserExternalIdentityError')

        identity_container = IUserExternalIdentityContainer(self.context)
        # pylint: disable=too-many-function-args
        identity_container.add_external_mapping(self._external_type,
                                                self._external_id)
        notify(ObjectModifiedFromExternalEvent(self.context))
        logger.info("Linking user to external id (%s) (external_type=%s) (external_id=%s",
                    self.context.username,
                    self._external_type,
                    self._external_id)
        return self.context


@view_config(route_name='objects.generic.traversal',
             name=VIEW_USER_UPSERT,
             renderer='rest',
             context=IDataserverFolder,
             request_method='POST')
class UserUpsertView(UserUpsertViewMixin):
    pass
interface.directlyProvides(UserUpsertView, INamedLinkView)


@view_config(name=VIEW_GRANT_USER_ACCESS,
             context=IDataserverFolder,
             route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST')
class UserGrantAccessView(GrantAccessViewMixin):
    pass


@view_config(name=VIEW_RESTRICT_USER_ACCESS,
             context=IDataserverFolder,
             route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST')
class UserRemoveAccessView(RemoveAccessViewMixin):
    pass
