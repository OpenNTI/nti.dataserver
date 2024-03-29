#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import BTrees
import itertools
import unicodecsv as csv

from datetime import datetime

from io import BytesIO

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

from six.moves.urllib_parse import unquote

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.catalog.catalog import ResultSet

from zope.event import notify

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users.views import raise_http_error

from nti.appserver.interfaces import UserCreatedByAdminWithRequestEvent

from nti.appserver.logon import _deal_with_external_account

from nti.appserver.policies.interfaces import IRequireSetPassword
from nti.appserver.policies.interfaces import INoAccountCreationEmail

from nti.appserver.ugd_query_views import UGDView

from nti.base._compat import text_

from nti.common.string import is_true
from nti.common.string import is_false

from nti.coremetadata.interfaces import IX_LASTSEEN_TIME
from nti.coremetadata.interfaces import IX_TOPICS as CM_IX_TOPICS
from nti.coremetadata.interfaces import IX_IS_DEACTIVATED

from nti.coremetadata.interfaces import IUsernameSubstitutionPolicy

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_admin
from nti.dataserver.authorization import is_site_admin
from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.contenttypes.forums.interfaces import ICommentPost
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

from nti.dataserver.users.utils import get_entity_email_from_index
from nti.dataserver.users.utils import get_entity_alias_from_index
from nti.dataserver.users.utils import get_entity_realname_from_index
from nti.dataserver.users.utils import get_entity_username_from_index
from nti.dataserver.users.utils import get_entity_mimetype_from_index

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IRecreatableUser
from nti.dataserver.users.interfaces import IUserUpdateUtility
from nti.dataserver.users.interfaces import IUsernameGeneratorUtility
from nti.dataserver.users.interfaces import IProfileDisplayableSupplementalFields

from nti.dataserver.users.interfaces import UpsertUserCreatedEvent
from nti.dataserver.users.interfaces import UpsertUserPreCreateEvent

from nti.dataserver.users.users import User

from nti.externalization import update_from_external_object

from nti.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.identifiers.utils import get_external_identifiers
from nti.identifiers.utils import get_user_for_external_id

from nti.mailer.interfaces import IEmailAddressable

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

    PINNED_SORT = True

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
                # Return post entry
                if IHeadlinePost.providedBy(obj):
                    obj = obj.__parent__
                # Do not return comments for entity activity
                if not ICommentPost.providedBy(obj):
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

    inputClass = (list, dict)

    def readInput(self, value=None):
        if self.request.body:
            values = super(AbstractUpdateView, self).readInput(value)
        else:
            values = self.request.params
        if isinstance(values, (list,tuple)):
            result = [CaseInsensitiveDict(x) for x in values]
        else:
            result = CaseInsensitiveDict(values)
        return result

    @Lazy
    def _params(self):
        """
        May be a dict of user input or a list of user inputs.
        """
        return self.readInput()

    def get_email(self, vals):
        """
        The email address by which we look up a user.
        """
        # pylint: disable=no-member
        result = vals.get('email', None) \
              or vals.get('mail', None)
        if not result and self.REQUIRE_EMAIL:
            raise_http_error(self.request,
                             _(u"Must provide email."),
                             u'NoEmailGiven')
        return result

    def get_external_id(self, vals):
        result = vals.get('id', None) \
              or vals.get('external_id', None) \
              or vals.get('identifier', None)
        return result and str(result)

    def get_external_type(self, vals):
        result = vals.get('external_type', None)
        return result and str(result)

    def get_username(self, vals):
        result = vals.get('user', None) \
              or vals.get('username', None)
        return result

    def get_user(self, vals):
        """
        Fetches a user based on the given external_type and external_id (or
        username).
        """
        external_type = self.get_external_type(vals)
        external_id = self.get_external_id(vals)
        username = self.get_username(vals)
        user = get_user_for_external_id(external_type, external_id)
        if user is None and username:
            user = User.get_user(username)
        return user

    def _predicate(self, user):
        """
        Only admins and site admins are allowed to update a user, raising
        otherwise.
        """
        result = is_admin_or_site_admin(self.remoteUser)
        if result:
            update_utility = IUserUpdateUtility(self.remoteUser, None)
            if update_utility is not None:
                if user is not None:
                    # pylint: disable=too-many-function-args
                    result = update_utility.can_update_user(user)
        if not result:
            raise_http_error(self.request,
                             _(u"Cannot update this user."),
                             u'CannotUpdateUserError',
                             factory=hexc.HTTPForbidden)

    def _process_user_data(self, user_data):
        user = self.get_user(user_data)
        self._predicate(user)
        return self._do_call(user_data)

    def __call__(self):
        if isinstance(self._params, (list,tuple)):
            # Batch processing - return appropriate indications of success/failure
            result = LocatedExternalList()
            processed_count = 0
            error_count = 0
            for user_data in self._params:
                try:
                    self._process_user_data(user_data)
                    processed_count += 1
                    msg = "Success"
                except Exception as exc:
                    error_count += 1
                    msg = text_(str(exc) or exc.i18n_message)
                result.append({"data": dict(user_data),
                               "message": msg})
            if error_count:
                # If errors, we must raise here to avoid any possible
                # partial state commits. The calling process must give
                # us a clean data set.
                result = to_external_object(result)
                raise_json_error(self.request,
                                 hexc.HTTPUnprocessableEntity,
                                 result,
                                 None)
            return result
        else:
            # A single input set - this is currently the most common use-case
            return self._process_user_data(self._params)


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

    def get_contextual_object(self, vals):
        """
        The contextual object that we want to grant access to.
        """
        # pylint: disable=no-member
        object_id = vals.get('ntiid') \
                 or vals.get('objectId') \
                 or vals.get('object_id')
        if not object_id:
            logger.warn('No ntiid given to update access (%s)', vals)
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

    def get_and_validate_user(self, vals):
        user = self.get_user(vals)
        if user is None:
            raise_http_error(self.request,
                             _(u"User not found."),
                             u'UserNotFoundError',
                             hexc.HTTPNotFound)
        return user

    def get_access_context(self, vals):
        # pylint: disable=no-member
        access_type = vals.get('scope') \
                   or vals.get('access_context') \
                   or vals.get('access_type')
        return access_type

    def _update_access(self, user, context, vals):
        access_provider = IAccessProvider(context, None)
        if access_provider is None:
            logger.warn('Invalid type to update access (%s)', context)
            raise_http_error(self.request,
                             _(u"Cannot grant access to object."),
                             u'ObjectNotAccessible')
        access_context = self.get_access_context(vals) or self.DEFAULT_ACCESS_CONTEXT
        result = access_provider.grant_access(user,
                                              access_context=access_context)
        return result
    _grant_access = _update_access

    def _handle_exception(self, exception, user, context_obj):
        if IGrantAccessException.providedBy(exception):
            logger.error('Error while granting access (%s) (%s)',
                         user,
                         context_obj)
            raise_http_error(self.request,
                             text_(str(exception) or exception.i18n_message),
                             u'ObjectNotAccessible')

    def _do_call(self, vals):
        user = context_obj = None
        try:
            user = self.get_and_validate_user(vals)
            context_obj = self.get_contextual_object(vals)
            result = self._update_access(user, context_obj, vals)
        except Exception as e:
            self._handle_exception(e, user, context_obj)
            raise
        if not result:
            # May already have access
            result = context_obj
        return result


class RemoveAccessViewMixin(GrantAccessViewMixin):
    """
    Removes access to a user and a contextual object. Typically this is a
    third-party removing access on behalf of a user.

    params:
        ntiid - the ntiid of the contextual object we remove access to

    returns HTTPNoContent
    """

    def _handle_exception(self, exception, user, context_obj):
        if IRemoveAccessException.providedBy(exception):
            logger.error('Error while removing access (%s) (%s)',
                         user,
                         context_obj)
            raise_http_error(self.request,
                             text_(str(exception) or exception.i18n_message),
                             u'CannotRestrictAccess')

    def _update_access(self, user, context, vals):
        access_provider = IAccessProvider(context, None)
        if access_provider is None:
            logger.warn('Invalid type to remove access (%s)', context)
            raise_http_error(self.request,
                             _(u"Cannot remove access to object."),
                             u'CannotRestrictAccess')
        result = access_provider.remove_access(user)
        return result
    _remove_access = _update_access

    def _do_call(self, vals):
        user = context_obj = None
        try:
            user = self.get_and_validate_user(vals)
            context_obj = self.get_contextual_object(vals)
            self._update_access(user, context_obj, vals)
        except Exception as e:
            self._handle_exception(e, user, context_obj)
            raise
        return hexc.HTTPNoContent()


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
    MARK_EMAIL_VERIFIED = True

    def is_recreatable_user(self):
        return False

    def should_require_password(self, vals):
        return is_true(vals.get('require_password'))

    def do_not_update(self, vals):
        return is_false(vals.get('update'))

    def _generate_username(self, vals):
        """
        Build an (opaque) username for this entity.
        """
        username_util = component.getUtility(IUsernameGeneratorUtility)
        return username_util.generate_username()

    def get_first_name(self, vals):
        result = vals.get('first', None) \
              or vals.get('firstname', None) \
              or vals.get('first_name', None)
        return result

    def get_last_name(self, vals):
        result = vals.get('last', None) \
              or vals.get('lastname', None) \
              or vals.get('last_name', None)
        return result

    def get_real_name(self, vals):
        # pylint: disable=no-member
        result = vals.get('real', None) \
              or vals.get('realname', None) \
              or vals.get('real_name', None)
        return result

    def find_real_name(self, vals):
        """
        Find real name from vals, validating if required.
        """
        result = self.get_real_name(vals)
        first_name = self.get_first_name(vals)
        last_name = self.get_last_name(vals)
        if not result and first_name and last_name:
            result = '%s %s' % (first_name, last_name)
        if not result and self.REQUIRE_NAME:
            raise_http_error(self.request,
                             _(u"Must provide real_name."),
                             u'NoRealNameGiven')
        return result

    def create_user(self, vals):
        username = self.get_username(vals)
        if not username:
            username = self._generate_username(vals)
        realname = self.find_real_name(vals)
        interface.alsoProvides(self.request, INoAccountCreationEmail)
        notify(UpsertUserPreCreateEvent(self.request))
        # Realname is used if we have it; otherwise first/last are used.
        email = self.get_email(vals)
        first_name = self.get_first_name(vals)
        last_name = self.get_last_name(vals)
        user = _deal_with_external_account(self.request,
                                           username=username,
                                           fname=first_name,
                                           lname=last_name,
                                           email=email,
                                           idurl=None,
                                           iface=None,
                                           user_factory=User.create_user,
                                           realname=realname,
                                           ext_values=vals)
        self.post_user_creation(user, vals)
        if self.is_recreatable_user():
            interface.alsoProvides(user, IRecreatableUser)
        notify(UpsertUserCreatedEvent(user, self.request))
        if self.should_require_password(vals):
            interface.alsoProvides(user, IRequireSetPassword)
            notify(UserCreatedByAdminWithRequestEvent(user, self.request))
        return user

    def post_user_creation(self, user, vals):
        """
        Subclasses can override this to implement behavior after a user is created.
        """
        external_type = self.get_external_type(vals)
        external_id = self.get_external_id(vals)
        if not external_type or not external_id:
            raise_http_error(self.request,
                             _(u"Must provide external_type and external_id."),
                             u'ExternalIdentifiersNotGivenError.')
        identity_container = IUserExternalIdentityContainer(user)
        # pylint: disable=too-many-function-args
        identity_container.add_external_mapping(external_type,
                                                external_id)

    def post_user_update(self, user, vals):
        """
        Subclasses can override this to implement behavior after a user is updated.
        """
        pass

    def update_user(self, user, vals):
        realname = self.find_real_name(vals)
        if realname is not None:
            friendly_named = IFriendlyNamed(user)
            friendly_named.realname = realname
        email = self.get_email(vals)
        if email is not None:
            profile = IUserProfile(user)
            profile.email = email
        # This is driven off the COMPLETE_USER_PROFILE_KEY annotation
        # so this profile could be a different implementation for different sites
        profile = IUserProfile(user)
        update_from_external_object(profile,
                                    vals)
        self.post_user_update(user, vals)

    def _do_call(self, vals):
        user = self.get_user(vals)
        if user is None:
            user = self.create_user(vals)
        elif self.do_not_update(vals):
            # Update unless they explicitly ask us not to (update=False)
            return False

        email = self.get_email(vals)
        logger.info('UserUpsert updating user (%s) (%s)',
                    user.username, email)
        self.update_user(user, vals)

        if email and self.MARK_EMAIL_VERIFIED:
            # XXX: This may longer hold true.
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

    def filter_intids(self, entity_ids):
        # TODO: We could also have a mimetype filter here
        result = entity_ids
        if self.onlyDeactivatedUsers:
            result = self.entity_catalog.family.IF.intersection(entity_ids,
                                                                self.deactivated_intids)
        elif self.onlyActivatedUsers:
            result = self.entity_catalog.family.IF.difference(entity_ids,
                                                              self.deactivated_intids)
        return result

    def get_sorted_entity_intids(self, doc_ids):
        """
        Returns an iterator of sorted entity intids.
        """
        # pylint: disable=unsupported-membership-test,no-member
        if self.sortOn and self.sortOn in self.sortMap:
            # Some indexes (e.g. alias) may not have all values. For now, we include
            # objects with empty values at the end.
            catalog = self.sortMap.get(self.sortOn)
            reverse = self.sortOrder == 'descending'
            sort_idx = catalog[self.sortOn]
            sort_idx_intids = BTrees.family64.IF.Set(sort_idx.ids())
            non_sort_intids = catalog.family.IF.difference(doc_ids, sort_idx_intids)
            doc_ids = sort_idx.sort(doc_ids, reverse=reverse)
            doc_ids = itertools.chain(doc_ids, non_sort_intids)
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
    
    def email(self, doc_id):
        return get_entity_email_from_index(doc_id, self.entity_catalog)

    def alias(self, doc_id):
        return get_entity_alias_from_index(doc_id, self.entity_catalog)

    def mime_type(self, doc_id):
        return get_entity_mimetype_from_index(doc_id, self.entity_catalog)

    @Lazy
    def onlyDeactivatedUsers(self):
        # pylint: disable=no-member
        return is_true(self.params.get('deactivated', 'False'))

    @Lazy
    def onlyActivatedUsers(self):
        # pylint: disable=no-member
        return is_false(self.params.get('deactivated', 'True'))

    @Lazy
    def deactivated_intids(self):
        """
        Return a set of site deactivated intids.
        """
        catalog = get_entity_catalog()
        deactivated_idx = catalog[CM_IX_TOPICS][IX_IS_DEACTIVATED]
        deactivated_ids = catalog.family.IF.Set(deactivated_idx.getIds() or ())
        return deactivated_ids

    def search_include(self, doc_id):
        result = True
        if self.searchTerm:
            # TODO should we have these in TextIndexes?
            # If so, we could avoid iterating over the potentially large
            # set of entity intids.
            op = self.search_prefix_match
            alias = self.alias(doc_id)
            realname = self.realname(doc_id)
            username = self.username(doc_id)
            email = self.email(doc_id)
            result = op(username, self.searchTerm) \
                  or op(realname, self.searchTerm) \
                  or op(alias, self.searchTerm) \
                  or op(email, self.searchTerm)
        return result

    def _batch_selector(self, entity):
        if self.reify_predicate(entity):
            return entity
        return None

    def reify_predicate(self, obj):  
        """
        Subclasses can override this.
        """
        return obj is not None

    @Lazy
    def site_name(self):
        return None
    
    @Lazy
    def filtered_intids(self):
        entity_intids = self.get_entity_intids(self.site_name)
        # We may have a generator here, we must resolve it before filtering
        entity_intids = self.entity_catalog.family.IF.Set(entity_intids)
        filtered_intids = self.filter_intids(entity_intids)
        return filtered_intids

    def _get_result_iter(self):
        sorted_entity_ids = self.get_sorted_entity_intids(self.filtered_intids)
        sorted_entity_ids = (x for x in sorted_entity_ids if self.search_include(x))
        intids = component.getUtility(IIntIds)
        rs = ResultSet(sorted_entity_ids, intids)
        return rs
    
    def _post_numeric_sorting(self, ext_res, sort_on, reverse):
        """
        Sorts the `Items` in the result dict in-place, using the sort_on
        and reverse params.
        """
        ext_res[ITEMS] = sorted(ext_res[ITEMS],
                                key=lambda x: getattr(x, sort_on, 0),
                                reverse=reverse)

    def _do_call(self):
        result = LocatedExternalDict()
        rs = self._get_result_iter()
        self._batch_items_iterable(result, rs, selector=self._batch_selector)
        # re/sort for numeric values
        if self.sortOn in self._NUMERIC_SORTING:
            # If we are sorting by time, we are indexed normalized to a minute.
            # We sort here by the actual value to correct this.
            reverse = self.sortOrder=='descending'
            self._post_numeric_sorting(result, self.sortOn, reverse)
        # transform only the required items
        result[ITEMS] = [
            self.transformer(x) for x in result[ITEMS]
        ]
        # XXX: Since we are using a generator above if we have a search param
        # we will not know the true count of possible search hits. This may
        # affect client side paging.
        item_count = len(result[ITEMS])
        batch_size,batch_start = self._get_batch_size_start()
        if item_count < batch_size:
            # We at least do not want to return pages if we do not have any
            result[TOTAL] = result['TotalItemCount'] = item_count + batch_start
        else:
            result[TOTAL] = result['TotalItemCount'] = len(self.filtered_intids)
        result[ITEM_COUNT] = len(result[ITEMS])
        return result
    

class AbstractUserViewMixin(AbstractEntityViewMixin):
    """
    An abstract view when getting lists of users.
    """
    
    _ALLOWED_SORTING = AbstractEntityViewMixin._ALLOWED_SORTING + (IX_LASTSEEN_TIME,)

    _NUMERIC_SORTING = AbstractEntityViewMixin._NUMERIC_SORTING + (IX_LASTSEEN_TIME,)
    
    def get_externalizer(self, user):
        # pylint: disable=no-member
        result = 'summary'
        if user == self.remoteUser:
            result = 'personal-summary'
        elif self.is_admin:
            result = 'admin-summary'
        elif    self.is_site_admin \
            and self.site_admin_utility.can_administer_user(self.remoteUser, user):
            result = 'admin-summary'
        return result

    @Lazy
    def sortMap(self):
        return {
            IX_ALIAS: get_entity_catalog(),
            IX_REALNAME: get_entity_catalog(),
            IX_DISPLAYNAME: get_entity_catalog(),
            IX_CREATEDTIME: get_metadata_catalog(),
            IX_LASTSEEN_TIME: get_metadata_catalog(),
        }
    

class UsersCSVExportMixin(object):
    """
    A mixin to utilize exporting users in a CSV file.
    """
    
    def _get_result_iter(self):
        raise NotImplementedError()
    
    def _get_filename(self):
        raise NotImplementedError()

    def _replace_username(self, username):
        substituter = component.queryUtility(IUsernameSubstitutionPolicy)
        if substituter is None:
            return username
        result = substituter.replace(username) or username
        return result

    def _get_email(self, user):
        addr = IEmailAddressable(user, None)
        return getattr(addr, 'email', '')

    def _format_time(self, t):
        try:
            return datetime.fromtimestamp(t).isoformat() if t else u''
        except ValueError:
            logger.debug("Cannot parse time '%s'", t)
            return str(t)

    def _build_user_info(self, user, profile_fields):
        username = user.username
        userid = self._replace_username(username)
        friendly_named = IFriendlyNamed(user)
        alias = friendly_named.alias
        email = self._get_email(user)
        createdTime = self._format_time(getattr(user, 'createdTime', 0))
        lastLoginTime = self._format_time(getattr(user, 'lastLoginTime', None))
        realname = friendly_named.realname
        external_id_map = get_external_identifiers(user)

        result = {
            'alias': alias,
            'email': email,
            'realname': realname,
            'username': userid,
            'createdTime': createdTime,
            'lastLoginTime': lastLoginTime,
            'external_ids': external_id_map
        }
        if profile_fields is not None:
            result.update(profile_fields.get_user_fields(user))
        return result

    def _create_csv_response(self):
        rs = self._get_result_iter()
        
        stream = BytesIO()
        fieldnames = ['username', 'realname', 'alias', 'email',
                      'createdTime', 'lastLoginTime']
        profile_fields = component.queryUtility(IProfileDisplayableSupplementalFields)
        if profile_fields is not None:
            fieldnames.extend(profile_fields.get_ordered_fields())

        user_infos = list()
        external_types = set()
        for user in rs:
            user_info = self._build_user_info(user, profile_fields)
            user_infos.append(user_info)
            user_ext_types = user_info.get('external_ids')
            external_types.update(user_ext_types)
        external_types = sorted(external_types)

        fieldnames.extend(external_types)
        csv_writer = csv.DictWriter(stream, 
                                    fieldnames=fieldnames,
                                    extrasaction='ignore',
                                    encoding='utf-8')
        csv_writer.writeheader()
            
        for user_info in user_infos:
            # With CSV, we only return one external_id mapping (common case).
            external_id_map = user_info.pop('external_ids')
            for external_type, external_id in external_id_map.items():
                user_info[external_type] = external_id
            csv_writer.writerow(user_info)

        response = self.request.response
        response.body = stream.getvalue()
        response.content_encoding = 'identity'
        response.content_type = 'text/csv; charset=UTF-8'
        response.content_disposition = 'attachment; filename="%s"' % self._get_filename()
        return response
    
    