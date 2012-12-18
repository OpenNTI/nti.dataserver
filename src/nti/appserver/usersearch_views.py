#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
View functions relating to searching for users.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import operator

from zope import component
from zope import interface
from zope.mimetype import interfaces as zmime_interfaces

from ZODB.utils import u64

from pyramid import security as sec
from pyramid.view import view_config

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import mimetype as nti_mimetype
from nti.dataserver import authorization as nauth
from nti.dataserver.users import interfaces as user_interfaces


from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict

import warnings

from . import interfaces as app_interfaces
from . import site_policies

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

	remote_user = users.User.get_user( sec.authenticated_userid( request ), dataserver=dataserver )
	partialMatch = request.matchdict['term']
	partialMatch = unicode(partialMatch or '').lower()
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


	return _format_result( result, remote_user, dataserver )

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

	remote_user = users.User.get_user( sec.authenticated_userid( request ), dataserver=dataserver )
	exact_match = request.matchdict['term']
	exact_match = unicode(exact_match or '').lower()
	entity = None

	if not remote_user or not exact_match:
		pass
	elif users.Entity.get_entity( exact_match ):
		# NOTE3: We have not stopped allowing this to work for user resolution.
		# This will probably break many assumptions in the UI about what and when usernames
		# can be resolved
		entity = users.Entity.get_entity( exact_match )
		# NOTE2: Going through this API lets some private objects be found
		# (DynamicFriendsLists, specifically). We should probably lock that down
	else:
		# To avoid ambiguity, we limit this to just friends lists.
		scoped = _search_scope_to_remote_user( remote_user, exact_match, op=operator.eq, fl_only=True )
		if not scoped:
			# Hmm. Ok, try everything else. Note that this could produce ambiguous results
			# in which case we make an arbitrary choice
			scoped = _search_scope_to_remote_user( remote_user, exact_match, op=operator.eq, ignore_fl=True )
		if scoped:
			entity = scoped.pop() # there can only be one exact match

	result = ()
	if entity is not None:
		if _make_visibility_test( remote_user )(entity):
			result = (entity,)

	return _format_result( result, remote_user, dataserver )

def _format_result( result, remote_user, dataserver ):
	# Since we are already looking in the object we might as well return the summary form
	# For this reason, we are doing the externalization ourself.
	result = [toExternalObject( user, name=('personal-summary'
											if user == remote_user
											else 'summary') )
				  for user in result]

	# We have no good modification data for this list, due to changing Presence
	# values of users, so it should not be cached, unfortunately
	result = LocatedExternalDict( {'Last Modified': 0, 'Items': result} )
	interface.alsoProvides( result, app_interfaces.IUncacheableInResponse )
	interface.alsoProvides( result, zmime_interfaces.IContentTypeAware )
	result.mime_type = nti_mimetype.nti_mimetype_with_class( None )
	result.__parent__ = dataserver.root
	result.__name__ = 'UserSearch' # TODO: Hmm
	return result

@interface.implementer(app_interfaces.IUsernameMatcher)
class _UsernameMatcher(object):
	
	def query(self, search_term, remote_user=None, provided=None):
		result = []
		dataserver = component.getUtility(nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout( dataserver ).users_folder
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
	
			if entity is not None and (provided is None or provided(entity)):
				result.append( entity )
				
		return result
	
def _authenticated_search( request, remote_user, dataserver, search_term ):
	
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder
	user_search_matcher = site_policies.queryAdapterInSite( remote_user, app_interfaces.IUserSearchPolicy, request=request )
	username_matcher = site_policies.queryUtilityInSite( app_interfaces.IUsernameMatcher, request=request )
	
	result = username_matcher.query(search_term, remote_user)
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
	:return: A set of matching objects, if any.
	"""
	result = set()
	if not ignore_fl:
		# Given a remote user, add matching friends lists, too
		for fl in remote_user.friendsLists.values():
			if not isinstance( fl, users.Entity ): # pragma: no cover
				continue
			names = user_interfaces.IFriendlyNamed( fl )
			if op( fl.username.lower(), search_term ) \
			   or op( (names.realname or '').lower(), search_term ) \
			   or op( (names.alias or '').lower(), search_term ):
				result.add( fl )
	if fl_only:
		return result

	# Also add enrolled classes
	# TODO: What about instructors?
	enrolled_sections = component.getAdapter( remote_user, app_interfaces.IContainerCollection, name='EnrolledClassSections' )
	for section in enrolled_sections.container:
		# TODO: We really want to be searching the class as well, but
		# we cannot get there from here
		if op( section.ID.lower(), search_term ) or op( section.Description.lower(), search_term ):
			result.add( section )

	if not result:
		warnings.warn( "Hack for UI: looking at display names of dynamic memberships (communities and DFLs)" )
		for x in remote_user.dynamic_memberships:
			if x and op( x.username.lower(), search_term.lower() ):
				result.add( x )
				break

	return result


def _make_visibility_test(remote_user):
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
