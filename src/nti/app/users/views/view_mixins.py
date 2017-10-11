#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.event import notify

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.appserver.logon import _deal_with_external_account

from nti.appserver.ugd_query_views import UGDView

from nti.base._compat import text_

from nti.dataserver import authorization as nauth

from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost

from nti.dataserver.interfaces import IAccessProvider
from nti.dataserver.interfaces import IGrantAccessException
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IUsernameGeneratorUtility

from nti.dataserver.metadata.index import IX_TOPICS
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import TP_TOP_LEVEL_CONTENT
from nti.dataserver.metadata.index import TP_DELETED_PLACEHOLDER

from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import get_users_by_email

from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.ntiids.ntiids import find_object_with_ntiid

logger = __import__('logging').getLogger(__name__)


def raise_http_error(request, message, code, factory=hexc.HTTPUnprocessableEntity):
    """
    Raise an HTTP json error.
    """
    raise_json_error(request,
                     factory,
                     {
                         'message': message,
                         'code': code,
                     },
                     None)


@view_config(route_name='objects.generic.traversal',
             name='Activity',
             request_method='GET',
             context=IDynamicSharingTargetFriendsList,
             permission=nauth.ACT_READ)
class EntityActivityViewMixin(UGDView):
    """
    A view to get activity for the given entity context. The remote
    user must be a member of the given entity.
    """

    def _set_user_and_ntiid(self, *unused_args, **unusedkwargs):
        self.ntiid = u''
        self.user = self.remoteUser

    def check_permission(self, context, unused_user):
        if self.remoteUser != context.creator and self.remoteUser not in context:
            raise hexc.HTTPForbidden()

    @property
    def _context_id(self):
        raise NotImplementedError()

    @property
    def _entity_board(self):
        raise NotImplementedError()

    @property
    def metadata_catalog(self):
        return get_metadata_catalog()

    def things(self, all_intids, intids):
        for uid in all_intids or ():
            obj = intids.queryObject(uid)
            if obj is not None:
                if IHeadlinePost.providedBy(obj):
                    obj = obj.__parent__  # return entry
                yield obj

    def getObjectsForId(self, *unused_args, **unused_kwargs):
        context = self.request.context
        catalog = self.metadata_catalog
        self.check_permission(context, self.remoteUser)
        intids = component.getUtility(IIntIds)

        username = self._context_id
        topics_idx = catalog[IX_TOPICS]
        shared_intids = catalog[IX_SHAREDWITH].apply({'any_of': (username,)})
        toplevel_extent = topics_idx[TP_TOP_LEVEL_CONTENT].getExtent()
        deleted_extent = topics_idx[TP_DELETED_PLACEHOLDER].getExtent()
        top_level_intids = toplevel_extent.intersection(shared_intids)

        seen = set()
        for forum in self._entity_board.values():
            seen.update(intids.queryId(t) for t in forum.values())
        seen.discard(None)
        topics_intids = intids.family.IF.LFSet(seen)

        all_intids = intids.family.IF.union(topics_intids, top_level_intids)
        all_intids = all_intids - deleted_extent
        items = list(self.things(all_intids, intids))
        return (items,)


class AbstractUpdateView(AbstractAuthenticatedView,
                         ModeledContentUploadRequestUtilsMixin):
    """
    An abstract view that takes uploaded input and updates a user. By default,
    a user is found based on their emai.
    """

    REQUIRE_EMAIL = False

    def readInput(self, value=None):
        if self.request.body:
            values = super(AbstractUpdateView, self).readInput(value)
        else:
            values = self.request.params
        result = CaseInsensitiveDict(values)
        return result

    @Lazy
    def _params(self):
        """
        A case insensitive dict of user input.
        """
        return self.readInput()

    @Lazy
    def _email(self):
        result = self._params.get('email') \
              or self._params.get('mail')
        if not result and self.REQUIRE_EMAIL:
            raise_http_error(self.request,
                             _(u"Must provide email."),
                             u'NoEmailGiven')
        return result

    def get_user(self):
        """
        Fetches a user based on the given email.
        """
        user = None
        if self._email is not None:
            users = get_users_by_email(self._email) or ()
            users = tuple(users)
            # XXX: Not sure if we want to handle multiple found users.
            if len(users) > 1:
                raise_http_error(self.request,
                             _(u"Multiple users found for email address."),
                             u'MultipleUsersFound')
            elif users:
                user = users[0]
        return user


class GrantAccessViewMixin(AbstractUpdateView):
    """
    Grants access to a user and a contextual object. Typically this is a
    third-party granting access on behalf of a user.

    params:
        ntiid - the ntiid of the contextual object we grant access to
        access_context - (optional) the scope of context access

    returns the access context
    """

    DEFAULT_ACCESS_CONTEXT = 'Public'

    @Lazy
    def _contextual_object(self):
        """
        The contextual object that we want to grant access to.
        """
        object_id = self._params.get('ntiid') \
                 or self._params.get('objectId') \
                 or self._params.get('object_id')
        if not object_id:
            logger.warn('No ntiid given to grant access (%s)', self._params)
            raise_http_error(self.request,
                             _(u"Must provide object to grant access to."),
                             u'NoObjectIDGiven')
        result = find_object_with_ntiid(object_id)
        if result is None:
            logger.warn('Object not found to grant access to (%s)', object_id)
            raise_http_error(self.request,
                             _(u"Object does not exist."),
                             u'ObjectNotFoundError',
                             hexc.HTTPNotFound)
        return result

    @Lazy
    def _user(self):
        user = self.get_user()
        if user is None:
            raise_http_error(self.request,
                             _(u"User not found."),
                             u'UserNotFoundError',
                             hexc.HTTPNotFound)
        return user

    @Lazy
    def _access_context(self):
        access_type = self._params.get('scope') \
                   or self._params.get('access_context') \
                   or self._params.get('access_type')
        return access_type

    def _grant_access(self, user, context):
        access_provider = IAccessProvider(context, None)
        if access_provider is None:
            logger.warn('Invalid type to grant access (%s)', context)
            raise_http_error(self.request,
                             _(u"Cannot grant access to object."),
                             u'ObjectNotAccessible')
        access_context = self._access_context or self.DEFAULT_ACCESS_CONTEXT
        result = access_provider.grant_access(user,
                                              access_context=access_context)
        return result

    def __call__(self):
        try:
            result = self._grant_access(self._user, self._contextual_object)
        except Exception as e:
            if IGrantAccessException.providedBy(e):
                logger.error('Error while granting access (%s) (%s)',
                             self._user,
                             self._contextual_object)
                raise_http_error(self.request,
                                 text_(str(e) or e.i18n_message),
                                 u'ObjectNotAccessible')
            raise
        if result is None:
            result = self._contextual_object
        return result


class UserUpsertViewMixin(AbstractUpdateView):
    """
    Update a user with the provided information. The user will be created if it
    does not already exist. This will typically be used by a third party on
    behalf of a user.

    params:
        first_name - the user's first name, only used if no `real_name` provided.
        last_name - the user's last name, only used if no `real_name` provided.
        real_name - if first/last name provided) the user's real name
        email - the user's email

    returns the user object
    """

    REQUIRE_NAME = False

    def _generate_username(self):
        """
        Build an (opaque) username for this entity.
        """
        username_util = component.getUtility(IUsernameGeneratorUtility)
        return username_util.generate_username()

    @Lazy
    def _first_name(self):
        result =  self._params.get('first') \
               or self._params.get('firstname') \
               or self._params.get('first_name')
        return result

    @Lazy
    def _last_name(self):
        result =  self._params.get('last') \
               or self._params.get('lastname') \
               or self._params.get('last_name')
        return result

    @Lazy
    def _real_name(self):
        result = self._params.get('real') \
              or self._params.get('realname') \
              or self._params.get('real_name')
        return result

    def _get_real_name(self):
        result = self._real_name
        if not self._real_name and self._first_name and self._last_name:
            result = '%s %s' % (self._first_name, self._last_name)
        if not result and self.REQUIRE_NAME:
            raise_http_error(self.request,
                             _(u"Must provide real_name."),
                             u'NoRealNameGiven')
        return result

    def create_user(self):
        username = self._generate_username()
        realname = self._get_real_name()
        # Realname is used if we have it; otherwise first/last are used.
        user = _deal_with_external_account(self.request,
                                           username=username,
                                           fname=self._first_name,
                                           lname=self._last_name,
                                           email=self._email,
                                           idurl=None,
                                           iface=None,
                                           user_factory=User.create_user,
                                           realname=realname)
        self.post_user_creation(user)
        return user

    def post_user_creation(self, user):
        """
        Subclasses can override this to implement behavior after a user is created.
        """
        pass

    def post_user_update(self, user):
        """
        Subclasses can override this to implement behavior after a user is updated.
        """
        pass

    def update_user(self, user):
        realname = self._get_real_name()
        friendly_named = IFriendlyNamed(user)
        friendly_named.realname = realname

        profile = IUserProfile(user)
        profile.email = self._email
        self.post_user_update(user)

    def __call__(self):
        user = self.get_user()
        if user is None:
            user = self.create_user()
        else:
            self.update_user(user)

        if self._email:
            # Trusted source for email verification
            profile = IUserProfile(user)
            profile.email_verified = True
        notify(ObjectModifiedFromExternalEvent(user))
        return user
