#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

from six.moves.urllib_parse import unquote

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.event import notify

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users.views import raise_http_error

from nti.appserver.logon import _deal_with_external_account

from nti.appserver.policies.interfaces import INoAccountCreationEmail

from nti.appserver.ugd_query_views import UGDView

from nti.base._compat import text_

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin
from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost

from nti.dataserver.interfaces import IAccessProvider
from nti.dataserver.interfaces import ISiteAdminUtility
from nti.dataserver.interfaces import IGrantAccessException
from nti.dataserver.interfaces import IRemoveAccessException
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.metadata.index import IX_TOPICS
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import TP_TOP_LEVEL_CONTENT
from nti.dataserver.metadata.index import TP_DELETED_PLACEHOLDER

from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.index import IX_ALIAS
from nti.dataserver.users.index import IX_REALNAME
from nti.dataserver.users.index import IX_DISPLAYNAME
from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.utils import get_entity_alias_from_index
from nti.dataserver.users.utils import get_entity_realname_from_index
from nti.dataserver.users.utils import get_entity_username_from_index

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IRecreatableUser
from nti.dataserver.users.interfaces import IUserUpdateUtility
from nti.dataserver.users.interfaces import IUsernameGeneratorUtility

from nti.dataserver.users.interfaces import UpsertUserCreatedEvent
from nti.dataserver.users.interfaces import UpsertUserPreCreateEvent

from nti.dataserver.users.users import User

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.identifiers.utils import get_user_for_external_id

from nti.ntiids.ntiids import find_object_with_ntiid

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


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

    # pylint: disable=arguments-differ
    def _set_user_and_ntiid(self, *unused_args, **unused_kwargs):
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

    # pylint: disable=arguments-differ
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
    An abstract view that takes uploaded input and updates a user. An external
    user is defined by a given external_type and external_id (and optionally a
    username).

    params:
        username - the username of the user to update
        external_type - the type of external identifier
        external_id - the external id of the user to update
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
        """
        The email address by which we look up a user.
        """
        # pylint: disable=no-member
        result = self._params.get('email') \
              or self._params.get('mail')
        if not result and self.REQUIRE_EMAIL:
            raise_http_error(self.request,
                             _(u"Must provide email."),
                             u'NoEmailGiven')
        return result

    @Lazy
    def _external_id(self):
        # pylint: disable=no-member
        result = self._params.get('id') \
              or self._params.get('external_id') \
              or self._params.get('identifier')
        return result and str(result)

    @Lazy
    def _external_type(self):
        # pylint: disable=no-member
        result = self._params.get('external_type')
        return result and str(result)

    @Lazy
    def _username(self):
        # pylint: disable=no-member
        result = self._params.get('user') \
              or self._params.get('username')
        return result

    def get_user(self):
        """
        Fetches a user based on the given external_type and external_id (or
        username).
        """
        user = get_user_for_external_id(self._external_type, self._external_id)
        if user is None and self._username:
            user = User.get_user(self._username)
        return user

    def _predicate(self):
        """
        Only admins and site admins are allowed to update a user, raising
        otherwise.
        """
        result = is_admin_or_site_admin(self.remoteUser)
        if result:
            update_utility = IUserUpdateUtility(self.remoteUser, None)
            if update_utility is not None:
                user = self.get_user()
                if user is not None:
                    # pylint: disable=too-many-function-args
                    result = update_utility.can_update_user(user)
        if not result:
            raise_http_error(self.request,
                             _(u"Cannot update this user."),
                             u'CannotUpdateUserError',
                             factory=hexc.HTTPForbidden)

    def __call__(self):
        self._predicate()
        # pylint: disable=no-member
        return self._do_call()


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
        # pylint: disable=no-member
        object_id = self._params.get('ntiid') \
                or self._params.get('objectId') \
                or self._params.get('object_id')
        if not object_id:
            logger.warn('No ntiid given to update access (%s)', self._params)
            raise_http_error(self.request,
                             _(u"Must provide object to grant access to."),
                             u'NoObjectIDGiven')
        result = find_object_with_ntiid(object_id)
        if result is None:
            logger.warn('Object not found to update access (%s)', object_id)
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
        # pylint: disable=no-member
        access_type = self._params.get('scope') \
                   or self._params.get('access_context') \
                   or self._params.get('access_type')
        return access_type

    def _update_access(self, user, context):
        access_provider = IAccessProvider(context, None)
        if access_provider is None:
            logger.warn('Invalid type to update access (%s)', context)
            raise_http_error(self.request,
                             _(u"Cannot grant access to object."),
                             u'ObjectNotAccessible')
        access_context = self._access_context or self.DEFAULT_ACCESS_CONTEXT
        result = access_provider.grant_access(user,
                                              access_context=access_context)
        return result
    _grant_access = _update_access

    def _handle_exception(self, exception):
        if IGrantAccessException.providedBy(exception):
            logger.error('Error while granting access (%s) (%s)',
                         self._user,
                         self._contextual_object)
            raise_http_error(self.request,
                             text_(str(exception) or exception.i18n_message),
                             u'ObjectNotAccessible')

    def _do_call(self):
        try:
            result = self._update_access(self._user, self._contextual_object)
        except Exception as e:
            self._handle_exception(e)
            raise
        if not result:
            # May already have access
            result = self._contextual_object
        return result


class RemoveAccessViewMixin(GrantAccessViewMixin):
    """
    Removes access to a user and a contextual object. Typically this is a
    third-party removing access on behalf of a user.

    params:
        ntiid - the ntiid of the contextual object we remove access to

    returns the access context
    """

    def _handle_exception(self, exception):
        if IRemoveAccessException.providedBy(exception):
            logger.error('Error while removing access (%s) (%s)',
                         self._user,
                         self._contextual_object)
            raise_http_error(self.request,
                             text_(str(exception) or exception.i18n_message),
                             u'CannotRestrictAccess')

    def _update_access(self, user, context):
        access_provider = IAccessProvider(context, None)
        if access_provider is None:
            logger.warn('Invalid type to remove access (%s)', context)
            raise_http_error(self.request,
                             _(u"Cannot remove access to object."),
                             u'CannotRestrictAccess')
        result = access_provider.remove_access(user)
        return result
    _remove_access = _update_access


class UserUpsertViewMixin(AbstractUpdateView):
    """
    Update a user with the provided information. The user will be created if it
    does not already exist. This will typically be used by a third party on
    behalf of a user.

    Users created through this process will not receive a new account email.

    params:
        first_name - the user's first name, only used if no `real_name` provided.
        last_name - the user's last name, only used if no `real_name` provided.
        real_name - if first/last name provided) the user's real name
        email - the user's email

    returns the user object
    """

    REQUIRE_NAME = False

    def is_recreatable_user(self):
        return False

    def _generate_username(self):
        """
        Build an (opaque) username for this entity.
        """
        username_util = component.getUtility(IUsernameGeneratorUtility)
        return username_util.generate_username()

    @Lazy
    def _first_name(self):
        # pylint: disable=no-member
        result = self._params.get('first') \
              or self._params.get('firstname') \
              or self._params.get('first_name')
        return result

    @Lazy
    def _last_name(self):
        # pylint: disable=no-member
        result = self._params.get('last') \
              or self._params.get('lastname') \
              or self._params.get('last_name')
        return result

    @Lazy
    def _real_name(self):
        # pylint: disable=no-member
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
        interface.alsoProvides(self.request, INoAccountCreationEmail)
        notify(UpsertUserPreCreateEvent(self.request))
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
        if self.is_recreatable_user():
            interface.alsoProvides(user, IRecreatableUser)
        notify(UpsertUserCreatedEvent(user, self.request))
        return user

    def post_user_creation(self, user):
        """
        Subclasses can override this to implement behavior after a user is created.
        """
        if not self._external_type or not self._external_id:
            raise_http_error(self.request,
                             _(u"Must provide external_type and external_id."),
                             u'ExternalIdentifiersNotGivenError.')
        identity_container = IUserExternalIdentityContainer(user)
        # pylint: disable=too-many-function-args
        identity_container.add_external_mapping(self._external_type,
                                                self._external_id)

    def post_user_update(self, user):
        """
        Subclasses can override this to implement behavior after a user is updated.
        """
        pass

    def update_user(self, user):
        realname = self._get_real_name()
        if realname is not None:
            friendly_named = IFriendlyNamed(user)
            friendly_named.realname = realname
        if self._email is not None:
            profile = IUserProfile(user)
            profile.email = self._email
        self.post_user_update(user)

    def _do_call(self):
        user = self.get_user()
        if user is None:
            user = self.create_user()
        else:
            logger.info('UserUpsert updating user (%s) (%s)',
                        user.username, self._email)
            self.update_user(user)

        if self._email:
            # Trusted source for email verification
            profile = IUserProfile(user)
            profile.email_verified = True
        notify(ObjectModifiedFromExternalEvent(user))
        return user


class AbstractEntityViewMixin(AbstractAuthenticatedView,
                              BatchingUtilsMixin):

    _DEFAULT_BATCH_SIZE = 30
    _DEFAULT_BATCH_START = 0

    _ALLOWED_SORTING = (IX_CREATEDTIME, IX_ALIAS, IX_REALNAME, IX_DISPLAYNAME)

    _NUMERIC_SORTING = (IX_CREATEDTIME,)

    def check_access(self):
        pass
        
    @Lazy
    def is_admin(self):
        return is_admin(self.remoteUser)

    @Lazy
    def is_site_admin(self):
        return is_site_admin(self.remoteUser)

    @Lazy
    def site_admin_utility(self):
        return component.getUtility(ISiteAdminUtility)

    @Lazy
    def params(self):
        return CaseInsensitiveDict(**self.request.params)

    @Lazy
    def sortOn(self):
        # pylint: disable=no-member
        sort = self.params.get('sortOn')
        return sort if sort in self._ALLOWED_SORTING else None

    @Lazy
    def searchTerm(self):
        # pylint: disable=no-member
        result = self.params.get('searchTerm') or self.params.get('filter')
        return unquote(result).lower() if result else None

    @property
    def sortOrder(self):
        # pylint: disable=no-member
        return self.params.get('sortOrder', 'ascending')

    @Lazy
    def entity_catalog(self):
        return get_entity_catalog()

    def get_externalizer(self, unused_entity):
        return ''

    def transformer(self, x):
        return to_external_object(x, name=self.get_externalizer(x))

    @Lazy
    def sortMap(self):
        return {
            IX_ALIAS: get_entity_catalog(),
            IX_REALNAME: get_entity_catalog(),
            IX_DISPLAYNAME: get_entity_catalog(),
            IX_CREATEDTIME: get_metadata_catalog(),
        }

    def get_entity_intids(self, site=None):
        raise NotImplementedError

    def get_sorted_entity_intids(self, site=None):
        doc_ids = self.get_entity_intids(site)
        # pylint: disable=unsupported-membership-test,no-member
        if self.sortOn and self.sortOn in self.sortMap:
            catalog = self.sortMap.get(self.sortOn)
            reverse = self.sortOrder == 'descending'
            doc_ids = catalog[self.sortOn].sort(doc_ids, reverse=reverse)
        return doc_ids

    def search_prefix_match(self, compare, search_term):
        compare = compare.lower() if compare else ''
        for k in compare.split():
            if k.startswith(search_term):
                return True
        return compare.startswith(search_term)

    def username(self, doc_id):
        return get_entity_username_from_index(doc_id, self.entity_catalog)

    def realname(self, doc_id):
        return get_entity_realname_from_index(doc_id, self.entity_catalog)
    
    def alias(self, doc_id):
        return get_entity_alias_from_index(doc_id, self.entity_catalog)

    def search_include(self, unused_doc_id, username, alias, realname):
        result = True
        if self.searchTerm:
            op = self.search_prefix_match
            result = op(username, self.searchTerm) \
                  or op(realname, self.searchTerm) \
                  or op(alias, self.searchTerm)
        return result

    def resolve_entity_ids(self, site=None):
        result = []
        for doc_id in self.get_sorted_entity_intids(site):
            if not self.searchTerm:
                result.append(doc_id)
            else:
                alias = self.alias(doc_id)
                realname = self.realname(doc_id)
                username = self.username(doc_id)
                if self.search_include(doc_id, username, alias, realname):
                    result.append(doc_id)
        return result

    def reify_predicate(self, obj):
        return obj is not None

    def reify(self, doc_ids):
        result = []
        intids = component.getUtility(IIntIds)
        for doc_id in doc_ids or ():
            obj = intids.queryObject(doc_id)
            if self.reify_predicate(obj):
                result.append(obj)
        return result

    def _do_call(self, site=None):
        result = LocatedExternalDict()
        items = self.resolve_entity_ids(site)
        self._batch_items_iterable(result, items)
        # reify only the required items
        result[ITEMS] = self.reify(result[ITEMS])
        # re/sort for numeric values
        if self.sortOn in self._NUMERIC_SORTING:
            # If we are sorting by time, we are indexed normalized to a minute.
            # We sort here by the actual value to correct this.
            reverse = self.sortOrder == 'descending'
            result[ITEMS] = sorted(result[ITEMS],
                                   key=lambda x: getattr(x, self.sortOn, 0),
                                   reverse=reverse)
        # transform only the required items
        result[ITEMS] = [
            self.transformer(x) for x in result[ITEMS] if x is not None
        ]
        result[TOTAL] = len(items)
        result[ITEM_COUNT] = len(result[ITEMS])
        return result
