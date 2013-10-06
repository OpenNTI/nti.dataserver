#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
View functions relating to searching for users.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import operator
import simplejson

from zope import component
from zope import interface
from zope.mimetype import interfaces as zmime_interfaces

from ZODB.utils import u64

from pyramid.view import view_config
from pyramid.threadlocal import get_current_request

from nti.appserver.policies import site_policies
from nti.appserver import httpexceptions as hexc
from nti.appserver._view_utils import get_remote_user
from nti.appserver import interfaces as app_interfaces

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import mimetype as nti_mimetype
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator
from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict


def _is_valid_search( search_term, remote_user ):
	"""Should the search be executed?

	In addition to enforcing an authenticated user, this places some limits on the
	size of the query (requiring a minimum) to avoid a search like 'e' which would match
	basically every user.
	"""
	return remote_user and search_term and len(search_term) >= 3

@view_config( route_name='search.users',
			  renderer='rest',
			  permission=nauth.ACT_SEARCH,
			  request_method='GET' )
def _UserSearchView(request):
	"""
	.. note:: This is extremely inefficient.

	.. note:: Policies need to be applied to this. For example, one policy
		is that we should only be able to find users that intersect the set of communities
		we are in. (To do that efficiently, we need community indexes).
	"""

	dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
	remote_user = get_remote_user( request, dataserver )
	assert remote_user is not None

	partialMatch = request.matchdict['term'] or ''
	if isinstance( partialMatch, bytes ):
		partialMatch = partialMatch.decode('utf-8')

	partialMatch = partialMatch.lower()
	# We tend to use this API as a user-resolution service, so
	# optimize for that case--avoid waking all other users up
	result = ()

	if _is_valid_search( partialMatch, remote_user ):
		# NOTE3: We have now stopped allowing this to work for user resolution.
		# This will probably break many assumptions in the UI about what and when usernames
		# can be resolved
		# NOTE2: Going through this API lets some private objects be found
		# (DynamicFriendsLists, specifically). We should probably lock that down
		result = _authenticated_search( request, remote_user, dataserver, partialMatch )
	elif partialMatch and remote_user:
		# Even if it's not a valid global search, we still want to
		# look at things local to the user
		result = _search_scope_to_remote_user( remote_user, partialMatch )

	request.response.cache_control.max_age = 120

	return _format_result( result, remote_user, dataserver )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  request_method='GET',
			  context=nti_interfaces.IUser,
			  custom_predicates=( (lambda context,request: get_remote_user(request) == context), ) )
def _ResolveMyself(request):
	"""
	Custom version of user resolution that only matches for ourself.
	"""
	# Our custom predicate protects us
	request.response.cache_control.max_age = 0
	request.response.etag = None
	# We don't want the simple summary, we want the personal summary, so we have
	# to do that ourself
	return toExternalObject(request.context, name='personal-summary-preferences')

@view_config( route_name='search.resolve_user',
			  renderer='rest',
			  permission=nauth.ACT_SEARCH,
			  request_method='GET' )
def _ResolveUserView(request):
	"""
	.. note:: This is extremely inefficient.

	.. note:: Policies need to be applied to this. For example, one policy
		is that we should only be able to find users that intersect the set of communities
		we are in. (To do that efficiently, we need community indexes).
	"""

	dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
	remote_user = get_remote_user( request, dataserver )
	assert remote_user is not None

	exact_match = request.matchdict['term']
	if not exact_match:
		raise hexc.HTTPNotFound()

	if isinstance( exact_match, bytes ):
		exact_match = exact_match.decode( 'utf-8' )

	result = _resolve_user(exact_match, remote_user)
	if result:
		# If we matched one user entity, see if we can get away without rendering it
		# TODO: This isn't particularly clean
		app_interfaces.IPreRenderResponseCacheController(result[0])(result[0], {'request': request} )
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
		request.response.cache_control.max_age = 600 # ten minutes

	formatted = _format_result(result, remote_user, dataserver)
	return formatted

@view_config(route_name='search.resolve_users',
			 renderer='rest',
			 permission=nauth.ACT_SEARCH,
			 request_method='POST')
def _ResolveUsersView(request):
	dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
	remote_user = get_remote_user(request, dataserver)
	assert remote_user is not None

	values = simplejson.loads(unicode(request.body, request.charset))
	usernames = values.get('usernames', values.get('terms', ()))
	if isinstance(usernames, six.string_types):
		usernames = usernames.split()

	result = {}
	for term in set(usernames):
		item = _resolve_user(term, remote_user)
		if item:
			match = item[0]
			app_interfaces.IPreRenderResponseCacheController(match)(match, {'request': request})
			result[match.username] = toExternalObject(match, name=('personal-summary'
													  if match == remote_user
													  else 'summary'))

	result = LocatedExternalDict({'Last Modified': 0, 'Items': result, 'Total':len(result)})
	return _provide_location(result, dataserver)

def _resolve_user(exact_match, remote_user):

	if isinstance(exact_match, bytes):
		exact_match = exact_match.decode('utf-8')

	exact_match = exact_match.lower()
	entity = users.Entity.get_entity(exact_match)
	# NOTE2: Going through this API lets some private objects be found if an NTIID is passed
	# (DynamicFriendsLists, specifically). We should probably lock that down

	if entity is None:
		# To avoid ambiguity, we limit this to just friends lists.
		scoped = _search_scope_to_remote_user(remote_user, exact_match, op=operator.eq, fl_only=True)
		if not scoped:
			# Hmm. Ok, try everything else. Note that this could produce ambiguous results
			# in which case we make an arbitrary choice
			scoped = _search_scope_to_remote_user(remote_user, exact_match, op=operator.eq, ignore_fl=True)
		if scoped:
			entity = scoped.pop()  # there can only be one exact match

	result = ()
	if entity is not None:
		if _make_visibility_test(remote_user)(entity):
			result = (entity,)
	return result

def _format_result(result, remote_user, dataserver):
	# Since we are already looking in the object we might as well return the summary form
	# For this reason, we are doing the externalization ourself.
	result = [toExternalObject(user, name=('personal-summary'
											if user == remote_user
											else 'summary'))
				for user in result]

	# We have no good modification data for this list, due to changing Presence
	# values of users, so caching is limited to etag matches
	result = LocatedExternalDict( {'Last Modified': 0, 'Items': result} )
	return _provide_location(result, dataserver)

def _provide_location(result, dataserver):
	interface.alsoProvides(result, app_interfaces.IUnModifiedInResponse)
	interface.alsoProvides(result, zmime_interfaces.IContentTypeAware)
	result.mimeType = nti_mimetype.nti_mimetype_with_class(None)
	result.__parent__ = dataserver.root
	result.__name__ = 'UserSearch'  # TODO: Hmm
	return result

def _authenticated_search( request, remote_user, dataserver, search_term ):
	result = []
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder
	user_search_matcher = site_policies.queryAdapterInSite( remote_user, app_interfaces.IUserSearchPolicy, request=request )
	# We used to have some nice heuristics about when to include uid-only
	# matches. This became much less valuable when we started to never display
	# anything except uid and sometimes to only want to search on UID:
	## Searching the userid is generally not what we want
	## now that we have username and alias (e.g,
	## tfandango@gmail.com -> Troy Daley. Search for "Dan" and get Troy and
	## be very confused.). As a compromise, we include them
	## if there are no other matches
	# Therefore we say screw it and throw that heuristic out the window.
	for entity_name in _users.iterkeys():
		__traceback_info__ = entity_name, search_term
		entity = None
		try:
			if search_term in entity_name.lower():
				entity = users.Entity.get_entity( entity_name, dataserver=dataserver )
		except KeyError: # pragma: no cover
			# Typically POSKeyError
			logger.warning( "Failed to search entity %s", entity_name )

		if entity is not None:
			result.append( entity )

	result.extend( user_search_matcher.query( search_term,
											  # Match Users and Communities here. Do not match IFriendsLists, because that
											  # would get private objects from other users.
											  provided=lambda x: nti_interfaces.IUser.providedBy( x ) or nti_interfaces.ICommunity.providedBy(x) ) )

	# FIXME: Hack in a policy of limiting searching to overlapping communities
	test = _make_visibility_test( remote_user )
	# Filter to things that share a common community
	result = {x for x in result if test(x)} # ensure a set

	# Add locally matching friends lists, etc. These don't need to go through the
	# filter since they won't be users
	result.update( _search_scope_to_remote_user( remote_user, search_term ) )

	return result

def _search_scope_to_remote_user( remote_user, search_term, op=operator.contains, fl_only=False, ignore_fl=False ):
	"""

	.. note:: This should be an extension point for new
		relationship types. We could look for 'search provider' components
		and use them.

	:param remote_user: The active User object.
	:param search_term: The (lowercase) search string.

	:return: A set of matching objects, if any.
	"""
	result = set()
	def check_entity( x ):
		# Run the search on the given entity, checking username and realname/alias
		# (This needs no policy because the user already has a relationship with this object,
		# either owning it or being a member). If it matches, it is placed
		# in the result set.
		if not isinstance( x, users.Entity ): # pragma: no cover
			return

		if op( x.username.lower(), search_term ):
			result.add( x )
		else:
			names = user_interfaces.IFriendlyNamed( x, None )
			if names:
				if	op((names.realname or '').lower(), search_term) \
					or op((names.alias or '').lower(), search_term):
					result.add(x)

	if not ignore_fl:
		# Given a remote user, add matching friends lists, too
		for fl in remote_user.friendsLists.values():
			check_entity( fl )
	if fl_only:
		return result

	# Search their dynamic memberships
	for x in remote_user.dynamic_memberships:
		check_entity( x )

	return result

def _make_visibility_test(remote_user):
	# TODO: Hook this up to the ACL support
	if remote_user:
		remote_com_names = remote_user.usernames_of_dynamic_memberships - set( ('Everyone',) )
		def test(x):
			try:
				getattr( x, 'username' )
			except KeyError: # pragma: no cover
				# typically POSKeyError
				logger.warning( "Failed to filter entity with id %s", hex(u64(x._p_oid)) )
				return False
			# User can see himself
			if x == remote_user:
				return True
			# User can see communities he's a member of
			if isinstance( x, users.Community ):
				return x.username in remote_com_names
			# No one can see the Koppa Kids
			# FIXME: Hardcoding this site/user policy
			if nti_interfaces.ICoppaUserWithoutAgreement.providedBy( x ):
				return False
			# Otherwise, visible if it doesn't have dynamic memberships, or we share dynamic memberships
			return not hasattr(x, 'usernames_of_dynamic_memberships') or x.usernames_of_dynamic_memberships.intersection( remote_com_names )
		return test
	return lambda x: True

@component.adapter(nti_interfaces.IUser)
@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class _SharedDynamicMembershipProviderDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, original, mapping):
		request = get_current_request()
		if request is not None:
			dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
			remote_user = get_remote_user(request, dataserver) if dataserver else None
			if 	remote_user is None or original == remote_user or \
				nti_interfaces.ICoppaUserWithoutAgreement.providedBy(original) or \
				not hasattr(original, 'usernames_of_dynamic_memberships'):
				return
			remote_dmemberships = remote_user.usernames_of_dynamic_memberships - set(('Everyone',))
			shared_dmemberships = original.usernames_of_dynamic_memberships.intersection(remote_dmemberships)
			mapping['SharedDynamicMemberships'] = list(shared_dmemberships)
