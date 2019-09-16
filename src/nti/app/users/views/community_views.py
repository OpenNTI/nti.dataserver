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
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.container.contained import Contained

from zope.container.interfaces import INameChooser

from zope.traversing.interfaces import IPathAdapter

from zope.event import notify

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentEditRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.users import MessageFactory as _

from nti.app.users.interfaces import ICommunitiesCollection
from nti.app.users.interfaces import IAllCommunitiesCollection

from nti.app.users.views import parse_mime_types

from nti.app.users.views.view_mixins import AbstractEntityViewMixin
from nti.app.users.views.view_mixins import EntityActivityViewMixin

from nti.appserver.pyramid_authorization import has_permission

from nti.common.string import is_true

from nti.coremetadata.interfaces import ICommunity
from nti.coremetadata.interfaces import ISiteCommunity
from nti.coremetadata.interfaces import IEntityIterable
from nti.coremetadata.interfaces import IDeactivatedCommunity
from nti.coremetadata.interfaces import DeactivatedCommunityEvent
from nti.coremetadata.interfaces import ReactivatedCommunityEvent

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization import is_site_admin
from nti.dataserver.authorization import is_admin_or_site_admin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users import User

from nti.dataserver.users.communities import Community

from nti.dataserver.users.index import IX_TOPICS
from nti.dataserver.users.index import IX_USERNAME
from nti.dataserver.users.index import IX_IS_COMMUNITY

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.interfaces import ICommunityProfile
from nti.dataserver.users.interfaces import IHiddenMembership
from nti.dataserver.users.interfaces import IUserUpdateUtility

from nti.dataserver.users.utils import get_users_by_site
from nti.dataserver.users.utils import intids_of_community_members
from nti.dataserver.users.utils import get_entity_mimetype_from_index

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid


ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(name='create_community')
@view_config(name='create.community')
@view_defaults(route_name='objects.generic.traversal',
               request_method='POST',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class AdminCreateCommunityView(AbstractAuthenticatedView,
                               ModeledContentUploadRequestUtilsMixin):
    """
    An NT admin view to create a community. NTI admins are able to define
    the username as well as designate the new community an
    :class:`ISiteCommunity`.
    """

    def __call__(self):
        externalValue = self.readInput()
        is_site_community = externalValue.pop('site_community', None) \
                         or externalValue.pop('is_site_community', None)
        is_site_community = is_true(is_site_community)
        username = externalValue.pop('username', None) \
                or externalValue.pop('Username', None)
        if not username:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a username.'),
                             },
                             None)
        community = Community.get_community(username)
        if community is not None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Community already exists.'),
                             },
                             None)
        args = {'username': username}
        args['external_value'] = externalValue
        self.request.response.status_int = 201  # created
        community = Community.create_community(**args)
        community.creator = self.remoteUser.username
        if is_site_community:
            interface.alsoProvides(community, ISiteCommunity)
        return community


@view_config(route_name='objects.generic.traversal',
             request_method='POST',
             context=IAllCommunitiesCollection,
             renderer='rest')
class CreateCommunityView(AbstractAuthenticatedView,
                          ModeledContentUploadRequestUtilsMixin):
    """
    A view on the :class:`IAllCommunitiesCollection` which will accept
    new communites tied to the current site.
    """

    RESTRICTED_FIELDS = ('Username', 'site_community', 'is_site_community')

    content_predicate = ICommunity.providedBy

    def readInput(self):
        result = super(CreateCommunityView, self).readInput()
        if result is not None:
            for key in self.RESTRICTED_FIELDS:
                result.pop(key, None)
        return result

    def generate_username(self, alias):
        """
        Return a username based on the alias of the form:

        alias@current_site.com.
        """
        site_name = getSite().__name__
        username = '%s@%s' % (alias, site_name)
        username = username.replace(' ', '_')
        dataserver = component.getUtility(IDataserver)
        users_folder = IShardLayout(dataserver).users_folder
        # XXX: Do we do this or do we raise because of conflict?
        name_chooser = INameChooser(users_folder)
        username = name_chooser.chooseName(username, object())
        return username

    def __call__(self):
        if not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden()
        externalValue = self.readInput()

        # Build the name based on the alias
        alias = externalValue.get('alias')
        if not alias:
            raise hexc.HTTPUnprocessableEntity()
        username = self.generate_username(alias)
        community = Community.create_community(username=username,
                                               external_value=externalValue)
        community.creator = self.remoteUser.username
        logger.info('Created community (%s) (%s) (%s)',
                    alias, username, self.remoteUser)
        return community


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_DELETE,
             request_method='DELETE',
             context=ICommunity)
class DeleteCommunityView(AbstractAuthenticatedView):

    def __call__(self):
        profile = ICommunityProfile(self.context, None)
        logger.info('Deleting community (%s) (%s) (%s)',
                    self.context.username,
                    getattr(profile, 'alias', ''),
                    self.remoteUser)
        if not IDeactivatedCommunity.providedBy(self.context):
            interface.alsoProvides(self.context, IDeactivatedCommunity)
            notify(ObjectModifiedFromExternalEvent(self.context))
            notify(DeactivatedCommunityEvent(self.context))
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_UPDATE,
             request_method='POST',
             name='Restore',
             context=ICommunity)
class RestoreCommunityView(AbstractAuthenticatedView):

    def __call__(self):
        profile = ICommunityProfile(self.context, None)
        logger.info('Restoring community (%s) (%s) (%s)',
                    self.context.username,
                    getattr(profile, 'alias', ''),
                    self.remoteUser)
        if IDeactivatedCommunity.providedBy(self.context):
            interface.noLongerProvides(self.context, IDeactivatedCommunity)
            notify(ObjectModifiedFromExternalEvent(self.context))
            notify(ReactivatedCommunityEvent(self.context))
        return self.context


@view_config(name='AllCommunities')
@view_config(name='list_communities')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class ListCommunitiesView(AbstractEntityViewMixin):

    def get_entity_intids(self, unused_site=None):
        catalog = self.entity_catalog
        # pylint: disable=unsubscriptable-object,no-member
        comms_idx = catalog[IX_TOPICS][IX_IS_COMMUNITY]
        result = catalog.family.IF.Set(comms_idx.getIds() or ())
        return result

    @Lazy
    def mimeTypes(self):
        # pylint: disable=no-member
        values = self.params
        mime_types = values.get('accept') \
                  or values.get('mime_types') \
                  or values.get('mimeTypes') or ''
        return parse_mime_types(mime_types)

    def search_include(self, doc_id):
        result = AbstractEntityViewMixin.search_include(self, doc_id)
        if result and self.mimeTypes:
            # pylint: disable=unsupported-membership-test
            mimeType = get_entity_mimetype_from_index(doc_id, self.entity_catalog)
            result = mimeType in self.mimeTypes
        return result

    def reify_predicate(self, obj):
        return ICommunity.providedBy(obj)

    def __call__(self):
        return self._do_call()


@view_config(route_name='objects.generic.traversal',
             context=ICommunity,
             request_method='PUT',
             permission=nauth.ACT_UPDATE,
             renderer='rest')
class UpdateCommunityView(AbstractAuthenticatedView,
                          ModeledContentEditRequestUtilsMixin,
                          ModeledContentUploadRequestUtilsMixin):

    content_predicate = ICommunity.providedBy

    def __call__(self):
        theObject = self.request.context
        self._check_object_exists(theObject)
        self._check_object_unmodified_since(theObject)
        externalValue = self.readInput()
        self.updateContentObject(theObject, externalValue)
        return theObject


@view_config(route_name='objects.generic.traversal',
             name='join',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_READ)
class JoinCommunityView(AbstractAuthenticatedView):

    def __call__(self):
        community = self.request.context
        if      (  not community.joinable \
                or community.auto_subscribe is not None) \
            and not has_permission(nauth.ACT_UPDATE, self.context):
            raise hexc.HTTPForbidden()

        user = self.remoteUser
        if user not in community:
            # pylint: disable=no-member
            user.record_dynamic_membership(community)
            user.follow(community)
        return community


@view_config(route_name='objects.generic.traversal',
             name='leave',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_READ)
class LeaveCommunityView(AbstractAuthenticatedView):

    def __call__(self):
        community = self.request.context
        if      (  not community.joinable \
                or community.auto_subscribe is not None) \
            and not has_permission(nauth.ACT_UPDATE, self.context):
            raise hexc.HTTPForbidden()

        user = self.remoteUser
        community = self.request.context
        if user in community:
            # pylint: disable=no-member
            user.record_no_longer_dynamic_member(community)
            user.stop_following(community)
        return community


@interface.implementer(IPathAdapter)
class CommunityMembersPathAdapter(Contained):

    __name__ = 'members'

    def __init__(self, context, request):
        self.context = self.community = context
        self.request = request
        self.__parent__ = context


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             context=CommunityMembersPathAdapter,
             permission=nauth.ACT_READ)
class CommunityMembersView(AbstractEntityViewMixin):

    def check_access(self):
        community = self.context.community
        if      not community.public \
            and self.remoteUser not in community \
            and not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden()
        return community

    def get_externalizer(self, user):
        # pylint: disable=no-member
        # It would be nice to make this automatic.
        result = 'summary'
        if user == self.remoteUser:
            result = 'personal-summary'
        elif self.is_admin:
            result = 'admin-summary'
        elif    self.is_site_admin \
            and self.site_admin_utility.can_administer_user(self.remoteUser, user):
            result = 'admin-summary'
        return result

    def username_index(self):
        entity_catalog = get_entity_catalog()
        return entity_catalog[IX_USERNAME]

    def get_entity_intids(self, unused_site=None):
        result = intids_of_community_members(self.context.community)
        username_index = self.username_index()
        return (x for x in result if x in username_index.documents_to_values)

    def reify_predicate(self, obj):
        return IUser.providedBy(obj)

    def __call__(self):
        self.check_access()
        result = self._do_call()
        return result


class AbstractUpdateMembershipView(AbstractAuthenticatedView,
                                   ModeledContentUploadRequestUtilsMixin):


    UPDATE_TYPE = None

    def readInput(self, value=None):
        if self.request.body:
            values = super(AbstractUpdateMembershipView, self).readInput(value)
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
    def community(self):
        return self.context.community

    @Lazy
    def _user_set(self):
        # pylint: disable=no-member
        user_set = self._params.get('users') \
                or self._params.get('usernames')
        result = []
        missing = []
        if user_set:
            user_set = user_set.split(',')
            if 'everyone' in user_set or 'Everyone' in user_set:
                logger.info('Adding all site users to community (%s)',
                            self.community.username)
                user_set = get_users_by_site()
            else:
                for username in user_set:
                    if is_valid_ntiid_string(username):
                        # Check if ntiid first
                        possible_user = find_object_with_ntiid(username)
                        if possible_user is None:
                            logger.info('Cannot add missing entity to community (%s)',
                                        username)
                            missing.append(username)
                            continue
                        if IUser.providedBy(possible_user):
                            result.append(possible_user)
                        else:
                            # Check and expand iterable
                            user_iterable = IEntityIterable(possible_user, None)
                            if user_iterable is not None:
                                result.extend(user_iterable)
                    else:
                        # The standard username case
                        user = User.get_user(username)
                        if user is None:
                            logger.info('Cannot add missing user to community (%s)',
                                        username)
                            missing.append(username)
                            continue
                        result.append(user)
        return result, missing

    def _update_user_membership(self, user):
        raise NotImplementedError()

    def process_users(self, users):
        """
        Process the user set, updating our community. Return the
        usernames of the updated, disallowed users, respectively.
        """
        update_utility = IUserUpdateUtility(self.remoteUser, None)
        updated_usernames = []
        disallowed_usernames = []
        remote_is_site_admin = is_site_admin(self.remoteUser)
        for user in users:
            # XXX: What do we do here for community admins
            # (non site admins)?
            if remote_is_site_admin:
                if      update_utility is not None \
                    and not update_utility.can_update_user(user):
                    disallowed_usernames.append(user.username)
                    continue
            self._update_user_membership(user)
            updated_usernames.append(user.username)
        return updated_usernames, disallowed_usernames

    def __call__(self):
        result = LocatedExternalDict()
        if not is_admin_or_site_admin(self.remoteUser):
            raise hexc.HTTPForbidden()
        user_set, missing = self._user_set()
        updated_users, not_allowed = self.process_users(user_set)

        result['Missing'] = missing
        result[self.UPDATE_TYPE] = updated_users
        result['NotAllowed'] = not_allowed

        result['MissingCount'] = len(missing)
        result['NotAllowedCount'] = len(not_allowed)
        result['%sCount' % self.UPDATE_TYPE] = len(updated_users)
        logger.info("%s community members (%s) (missing=%s) (not_allowed=%s) (updated=%s)",
                    self.UPDATE_TYPE,
                    self.community.username,
                    missing,
                    not_allowed,
                    len(updated_users))
        return result


@view_config(route_name='objects.generic.traversal',
             request_method='POST',
             context=CommunityMembersPathAdapter,
             permission=nauth.ACT_UPDATE)
class CommunityMembersAddView(AbstractUpdateMembershipView):
    """
    API to manage user membership within a community
    """

    UPDATE_TYPE = 'Added'

    def _update_user_membership(self, user):
        user.record_dynamic_membership(self.community)
        user.follow(self.community)


@view_config(route_name='objects.generic.traversal',
             name='bulk_remove',
             request_method='POST',
             context=CommunityMembersPathAdapter,
             permission=nauth.ACT_UPDATE)
class CommunityMembersRemoveView(AbstractUpdateMembershipView):
    """
    API to remove user membership within a community
    """

    UPDATE_TYPE = 'Removed'

    def _update_user_membership(self, user):
        user.record_no_longer_dynamic_member(self.community)
        user.stop_following(self.community)


@view_config(route_name='objects.generic.traversal',
             name='hide',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_READ)
class HideCommunityMembershipView(AbstractAuthenticatedView):

    def __call__(self):
        user = self.remoteUser
        community = self.request.context
        hidden = IHiddenMembership(community)
        if user in community and user not in hidden:
            # pylint: disable=too-many-function-args
            hidden.hide(user)
        return community


@view_config(route_name='objects.generic.traversal',
             name='unhide',
             request_method='POST',
             context=ICommunity,
             permission=nauth.ACT_READ)
class UnhideCommunityMembershipView(AbstractAuthenticatedView):

    def __call__(self):
        user = self.remoteUser
        community = self.request.context
        hidden = IHiddenMembership(community)
        if user in hidden:
            hidden.unhide(user)
        return community


@view_config(route_name='objects.generic.traversal',
             name='Activity',
             request_method='GET',
             context=ICommunity,
             permission=nauth.ACT_READ)
class CommunityActivityView(EntityActivityViewMixin):

    def _set_user_and_ntiid(self, *unused_args, **unused_kwargs):
        self.ntiid = u''
        self.user = self.remoteUser

    def _get_security_check(self):
        def security_check(unused_x):
            return True
        return False, security_check

    def check_permission(self, context, user):
        # Parent requires creator or member; we override that.
        # Members can only view if public (?)
        # ...or an admin
        if      (    not context.public
                 and user not in context) \
            and not has_permission(nauth.ACT_UPDATE, context):
            raise hexc.HTTPForbidden()

    @property
    def _context_id(self):
        # pylint: disable=no-member
        return self.context.username

    @property
    def _entity_board(self):
        return ICommunityBoard(self.request.context, None) or {}


class CommunityAdminMixin(object):

    def get_usernames(self):
        values = self.readInput()
        usernames = values.get('usernames') or values.get('username')
        usernames = usernames.split(',')
        return usernames


@view_config(route_name='objects.generic.traversal',
             context=ICommunity,
             request_method='PUT',
             permission=nauth.ACT_UPDATE,
             name='AddAdmin')
class AddCommunityAdmin(AbstractAuthenticatedView,
                        ModeledContentUploadRequestUtilsMixin,
                        CommunityAdminMixin):
    """
    Updates a list of usernames to the admin role for a community
    If the user is not currently in the community they are added
    """

    def __call__(self):
        community = self.context
        for username in self.get_usernames():
            user = User.get_user(username)
            if user is None:
                logger.debug(u'Failed to add username %s to community %s' % (username, community.username))
                raise hexc.HTTPUnprocessableEntity(u'Username %s does not exist' % username)
            if user not in community:
                # pylint: disable=no-member
                user.record_dynamic_membership(community)
                user.follow(community)
            community.add_admin(username)
        return hexc.HTTPOk()


@view_config(route_name='objects.generic.traversal',
             context=ICommunity,
             request_method='PUT',
             permission=nauth.ACT_UPDATE,
             name='RemoveAdmin')
class RemoveCommunityAdmin(AbstractAuthenticatedView,
                           CommunityAdminMixin,
                           ModeledContentUploadRequestUtilsMixin):
    """
    Removes a list of usernames from the admin role for a community
    """

    def __call__(self):
        community = self.context
        for username in self.get_usernames():
            user = User.get_user(username)
            if user is None:
                logger.debug(u'Failed to remove username %s from community %s' % (username, community.username))
                raise hexc.HTTPUnprocessableEntity(u'Username %s does not exist' % username)
            if user not in community:
                raise hexc.HTTPUnprocessableEntity(u'Username %s is not a community member' % username)
            community.remove_admin(username)
        return hexc.HTTPOk()


@view_config(route_name='objects.generic.traversal',
             context=ICommunity,
             request_method='GET',
             permission=nauth.ACT_UPDATE,
             name='ListAdmins')
class ListCommunityAdmins(AbstractAuthenticatedView,
                          CommunityAdminMixin):

    def __call__(self):
        result = LocatedExternalList()
        usernames = self.context.get_admin_usernames()
        for username in usernames:
            result.append(User.get_user(username))
        return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICommunitiesCollection,
             permission=nauth.ACT_READ,
             request_method='GET')
class CommunityCollectionView(AbstractAuthenticatedView,
                              BatchingUtilsMixin):
    """
    A generic :class:`ICommunitiesCollection` view that supports paging on the
    collection.
    """

    _DEFAULT_BATCH_SIZE = None
    _DEFAULT_BATCH_START = None

    def __call__(self):
        result = to_external_object(self.context)
        # We have a dict here
        result[ITEMS] = result[ITEMS].values()
        result[TOTAL] = len(result[ITEMS])
        self._batch_items_iterable(result,
                                   result[ITEMS],
                                   number_items_needed=result[TOTAL])
        return result
