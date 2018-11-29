#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
View functions relating to searching for users.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import itertools

import six
import operator
import simplejson
from collections import Mapping
from six.moves.urllib_parse import unquote

from zope import component
from zope import interface

from zope.mimetype.interfaces import IContentTypeAware

from ZODB.utils import u64

from pyramid.threadlocal import get_current_request

from pyramid.view import view_config

from nti.app.authentication import get_remote_user

from nti.app.externalization.internalization import handle_unicode

from nti.app.renderers.interfaces import IUnModifiedInResponse
from nti.app.renderers.interfaces import IPreRenderResponseCacheController

from nti.appserver import httpexceptions as hexc

from nti.appserver.interfaces import INamedLinkView
from nti.appserver.interfaces import IUserSearchPolicy

from nti.base._compat import text_

from nti.common.string import is_false

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IEntityContainer
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import ISiteAdminUtility
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement
from nti.dataserver.interfaces import IUseNTIIDAsExternalUsername
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.entity import Entity

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.externalization.externalization import toExternalObject

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import Singleton

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.ntiids.oids import to_external_ntiid_oid
from nti.site.site import get_component_hierarchy_names
from nti.app.users.utils import get_user_creation_sitename

logger = __import__('logging').getLogger(__name__)

MAX_USERSEARCH_RESULTS = 1000

def _max_results():
    return MAX_USERSEARCH_RESULTS

def _is_valid_search(search_term, remote_user):
    """
    Should the search be executed?

    In addition to enforcing an authenticated user, this places some limits on the
    size of the query (requiring a minimum) to avoid a search like 'e' which would match
    basically every user.
    """
    return remote_user and search_term and len(search_term) >= 3


@view_config(route_name='objects.generic.traversal',
             name='UserSearch',
             renderer='rest',
             context=IDataserverFolder,
             permission=nauth.ACT_SEARCH,
             request_method='GET')
def _UserSearchView(request):
    """
    :param bool no_filter: If given and true, then will return users from all sites
    if the remoteUser in the request is an admin. Otherwise, only searches users who
    belong to the community of the site in which the request is being performed.
    Searching in a site without a community will return users from all sites.

    .. note:: This is extremely inefficient.

    .. note:: Policies need to be applied to this. For example, one policy
            is that we should only be able to find users that intersect the set of communities
            we are in. (To do that efficiently, we need community indexes).
    """
    dataserver = request.registry.getUtility(IDataserver)
    remote_user = get_remote_user(request, dataserver)
    assert remote_user is not None

    partialMatch = request.subpath[0] if request.subpath else ''
    partialMatch = text_(partialMatch)
    partialMatch = unquote(partialMatch)
    partialMatch = partialMatch.lower()

    # We tend to use this API as a user-resolution service, so
    # optimize for that case--avoid waking all other users up
    result = ()
    if _is_valid_search(partialMatch, remote_user):
        # NOTE3: We have now stopped allowing this to work for user resolution.
        # This will probably break many assumptions in the UI about what and when usernames
        # can be resolved
        # NOTE2: Going through this API lets some private objects be found
        # (DynamicFriendsLists, specifically). We should probably lock that down
        result = _authenticated_search(remote_user, partialMatch, request)
    elif partialMatch and remote_user:
        # Even if it's not a valid global search, we still want to
        # look at things local to the user
        result = _search_scope_to_remote_user(remote_user, partialMatch)

    request.response.cache_control.max_age = 120

    # limit to the first MAX_USERSEARCH_RESULTS
    result = itertools.islice(result, _max_results())

    result = _format_result(result, remote_user, dataserver)
    return result
interface.directlyProvides(_UserSearchView, INamedLinkView)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_READ,
             request_method='GET',
             context=IUser,
             custom_predicates=((lambda context, request: get_remote_user(request) == context),))
def _TraverseToMyself(request):
    """
    Custom version of user resolution that only matches for ourself.
    """
    # Our custom predicate protects us
    request.response.etag = None
    request.response.cache_control.max_age = 0

    # We don't want the simple summary, we want the personal summary, so we have
    # to do that ourself
    result = toExternalObject(request.context,
                              name='personal-summary-preferences')
    return result


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             permission=nauth.ACT_READ,
             request_method='GET',
             context=IUser)
def _TraverseToUser(request):
    """
    When we traverse to a user, we don't want to wrap him in a collection
    (as we used to) we want to treat it like user resolutaion
    """
    remote_user = get_remote_user(request)
    if _make_visibility_test(remote_user)(request.context):
        return request.context
    raise hexc.HTTPForbidden()


@view_config(route_name='objects.generic.traversal',
             context=IDataserverFolder,
             name='ResolveUser',
             renderer='rest',
             permission=nauth.ACT_SEARCH,
             request_method='GET')
def _ResolveUserView(request):
    """
    .. note:: This is extremely inefficient.

    .. note:: Policies need to be applied to this. For example, one policy
            is that we should only be able to find users that intersect the set of communities
            we are in. (To do that efficiently, we need community indexes).
    """

    dataserver = request.registry.getUtility(IDataserver)
    remote_user = get_remote_user(request, dataserver)
    assert remote_user is not None

    exact_match = request.subpath[0] if request.subpath else ''
    if not exact_match:
        raise hexc.HTTPNotFound()
    exact_match = text_(exact_match)
    exact_match = unquote(exact_match)

    admin_filter_by_site_community = not is_false(
                        request.params.get('filter_by_site_community'))

    result = _resolve_user(exact_match, remote_user, admin_filter_by_site_community)
    if result:
        # If we matched one user entity, see if we can get away without rendering it
        # TODO: This isn't particularly clean
        controller = IPreRenderResponseCacheController(result[0])
        controller(result[0], {'request': request})
        # special case the remote user being the same user; we don't want to cache
        # ourself based simply on modification date as that doesn't take into account
        # dynamic links; we do need to render
        if result[0] == remote_user:
            request.response.cache_control.max_age = 0
            request.response.etag = None
    else:
        # Let resolutions that failed be cacheable for a long time.
        # It's extremely unlikely that someone is going to snag this missing
        # username in the next little bit
        request.response.cache_control.max_age = 600  # ten minutes

    formatted = _format_result(result, remote_user, dataserver)
    return formatted
interface.directlyProvides(_ResolveUserView, INamedLinkView)


@view_config(route_name='objects.generic.traversal',
             context=IDataserverFolder,
             name='ResolveUsers',
             renderer='rest',
             permission=nauth.ACT_SEARCH,
             request_method='POST')
def _ResolveUsersView(request):
    dataserver = request.registry.getUtility(IDataserver)
    remote_user = get_remote_user(request, dataserver)
    assert remote_user is not None

    admin_filter_by_site_community = not is_false(
                        request.params.get('filter_by_site_community'))

    values = simplejson.loads(handle_unicode(request.body, request))
    if isinstance(values, Mapping):
        usernames = values.get('usernames') or values.get('terms') or ()
    elif isinstance(usernames, six.string_types):
        usernames = usernames.split()

    result = {}
    for term in set(usernames or ()):
        item = _resolve_user(term, remote_user, admin_filter_by_site_community)
        if item:
            match = item[0]
            controller = IPreRenderResponseCacheController(match)
            controller(match, {'request': request})
            if IDynamicSharingTargetFriendsList.providedBy(match):
                keyname = match.NTIID
            elif IUseNTIIDAsExternalUsername.providedBy(match):
                keyname = to_external_ntiid_oid(match)
            else:
                keyname = match.username
            result[keyname] = toExternalObject(match, name=('personal-summary'
                                                            if match == remote_user
                                                            else 'summary'))

    result = LocatedExternalDict({'Last Modified': 0,
                                  'Items': result,
                                  'Total': len(result)})
    return _provide_location(result, dataserver)
interface.directlyProvides(_ResolveUsersView, INamedLinkView)


def _resolve_user(exact_match, remote_user, admin_filter_by_site_community):
    exact_match = text_(exact_match)
    # This does an NTIID lookup if needed, so we can't alter the case yet
    entity = Entity.get_entity(exact_match)
    # NOTE2: Going through this API lets some private objects be found if an NTIID is passed
    # (DynamicFriendsLists, specifically). We should probably lock that down
    if entity is None:
        exact_match = exact_match.lower()
        # To avoid ambiguity, we limit this to just friends lists.
        scoped = _search_scope_to_remote_user(remote_user, exact_match,
                                              op=operator.eq, fl_only=True)
        if not scoped:
            # Hmm. Ok, try everything else. Note that this could produce ambiguous results
            # in which case we make an arbitrary choice
            scoped = _search_scope_to_remote_user(remote_user, exact_match,
                                                  op=operator.eq, ignore_fl=True)
        if scoped:
            entity = scoped.pop()  # there can only be one exact match

    result = ()
    if entity is not None:
        if _make_visibility_test(remote_user, admin_filter_by_site_community)(entity):
            result = (entity,)
    return result


def _format_result(result, remote_user, dataserver):
    def _get_ext_type(user_tocheck):
        ext_type = 'summary'
        if user_tocheck == remote_user:
            # Since we are already looking in the object we might as well
            # return the summary form.
            ext_type = 'personal-summary'
        elif nauth.is_admin_or_content_admin_or_site_admin(remote_user):
            ext_type = 'admin-summary'
        return ext_type

    result = [toExternalObject(user, name=(_get_ext_type(user)))
              for user in result]

    # We have no good modification data for this list, due to changing Presence
    # values of users, so caching is limited to etag matches
    result = LocatedExternalDict({'Last Modified': 0, 'Items': result})
    return _provide_location(result, dataserver)


def _provide_location(result, dataserver):
    interface.alsoProvides(result, IUnModifiedInResponse)
    interface.alsoProvides(result, IContentTypeAware)
    result.mimeType = nti_mimetype_with_class(None)
    result.__parent__ = dataserver.root
    result.__name__ = 'UserSearch'  # TODO: Hmm
    return result


def _authenticated_search(remote_user, search_term, request):
    # Match Users and Communities here. Do not match IFriendsLists, because
    # that would get private objects from other users.
    def _selector(x):
        result = IUser.providedBy(x) \
            or (ICommunity.providedBy(x) and x.public)
        return result

    user_search_matcher = IUserSearchPolicy(remote_user)
    result = user_search_matcher.query(search_term,
                                       provided=_selector)

    # By default, filter by site community for admins.
    admin_filter_by_site_community = not is_false(
        request.params.get('filter_by_site_community'))

    # Filter to things that share a common community
    # FIXME: Hack in a policy of limiting searching to overlapping communities
    test = _make_visibility_test(remote_user, admin_filter_by_site_community)
    result = {x for x in result if test(x)}  # ensure a set

    # Add locally matching friends lists, etc. These don't need to go through the
    # filter since they won't be users
    result.update(_search_scope_to_remote_user(remote_user, search_term))
    return result


def _scoped_search_prefix_match(compare, search_term):
    for k in compare.split():
        if k.startswith(search_term):
            return True
    return compare.startswith(search_term)


def _search_scope_to_remote_user(remote_user, search_term, op=_scoped_search_prefix_match,
                                 fl_only=False, ignore_fl=False):
    """
    .. note:: This should be an extension point for new
            relationship types. We could look for 'search provider' components
            and use them.

    :param remote_user: The active User object.
    :param search_term: The (lowercase) search string.
    :keyword op: A callable of two string objects, a username to examine
            and the search term. This means it can be something like :func:`operator.contains`
            to do a partial substring match, or :func:`operator.eq` to do an equality
            check. The default does a prefix match on each space separated component.

    :return: A :class:`set` of matching objects, if any.
    """

    result = set()
    everyone = Entity.get_entity('Everyone')

    def check_entity(x):
        if x == everyone:
            return
        # Run the search on the given entity, checking username and realname/alias
        # (This needs no policy because the user already has a relationship with this object,
        # either owning it or being a member). If it matches, it is placed
        # in the result set.
        if not IEntity.providedBy(x):  # pragma: no cover
            return

        if op(x.username.lower(), search_term):
            result.add(x)
        else:
            names = IFriendlyNamed(x, None)
            if names:
                if     (names.realname and op(names.realname.lower(), search_term)) \
                    or (names.alias and op(names.alias.lower(), search_term)):
                    result.add(x)

    if not ignore_fl:
        # Given a remote user, add matching friends lists, too
        for fl in remote_user.friendsLists.values():
            check_entity(fl)
    if fl_only:
        return result

    # Search their dynamic memberships
    for x in remote_user.dynamic_memberships:
        check_entity(x)

    return result


def _make_visibility_test(remote_user, admin_filter_by_site_community=True):
    """
    NT Admins can see any user
    If filtering by site, they can resolve any user in this site or from any
    parent site.

    Site admins can only see those users they are permissioned to administser.

    Normal users can only resolve those users with intersecting community
    membership.
    """
    # TODO: Hook this up to the ACL support
    if remote_user:
        is_admin = nauth.is_admin_or_content_admin(remote_user)
        is_site_admin = nauth.is_site_admin(remote_user)
        site_admin_utility = component.getUtility(ISiteAdminUtility)

        site_names = get_component_hierarchy_names()

        if is_admin:
            # If we're an admin, we can search everyone unless we are filtering
            # by user creation site (this site plus any parent site).
            def site_check(unused_target_user):
                return True

            if admin_filter_by_site_community:
                def site_check(target_user):
                    user_site = get_user_creation_sitename(target_user)
                    return not user_site or not site_names or user_site in site_names
        else:
            # Visible if it doesn't have dynamic memberships,
            # or we share dynamic memberships
            memberships = remote_user.usernames_of_dynamic_memberships
            remote_com_names = memberships - set(('Everyone',))
            def site_check(target_user):
                return not hasattr(target_user, 'usernames_of_dynamic_memberships') \
                    or target_user.usernames_of_dynamic_memberships.intersection(remote_com_names)

        def test(x):
            try:
                getattr(x, 'username')
            except KeyError:  # pragma: no cover
                # typically POSKeyError
                logger.warning("Failed to filter entity with id %s",
                               hex(u64(x._p_oid)))
                return False
            # User can see himself
            if x is remote_user:
                return True

            # public comms can be searched
            if      ICommunity.providedBy(x) \
                and (x.public or is_admin or is_site_admin):
                return True

            # Site admins can only view users in their site; otherwise fall
            # back to membership intersection
            if      is_site_admin \
                and site_admin_utility.can_administer_user(remote_user, x, remote_com_names):
                return True

            # No one can see the Koppa Kids
            # FIXME: Hardcoding this site/user policy
            if      ICoppaUserWithoutAgreement.providedBy(x) \
                and not is_admin \
                and not is_site_admin:
                return False

            # User can see dynamic memberships he's a member of
            # or owns. First, the general case
            container = IEntityContainer(x, None)
            if container is not None and not is_admin:
                return remote_user in container or getattr(x, 'creator', None) is remote_user

            return site_check(x)
        return test

    # Return false if we don't have a remote user for some reason
    return lambda unused_x: False


@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _SharedDynamicMembershipProviderDecorator(Singleton):

    def decorateExternalMapping(self, original, mapping):
        request = get_current_request()
        if request is not None:
            dataserver = request.registry.getUtility(IDataserver)
            remote_user = get_remote_user(
                request, dataserver) if dataserver else None
            if     remote_user is None or original == remote_user \
                or ICoppaUserWithoutAgreement.providedBy(original) \
                or not hasattr(original, 'usernames_of_dynamic_memberships'):
                return
            remote_dmemberships = remote_user.usernames_of_dynamic_memberships
            remote_dmemberships = remote_dmemberships - set(('Everyone',))

            dynamic_memberships = original.usernames_of_dynamic_memberships
            shared_dmemberships = dynamic_memberships.intersection(
                remote_dmemberships)
            mapping['SharedDynamicMemberships'] = list(shared_dmemberships)
