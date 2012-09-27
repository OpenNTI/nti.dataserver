#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
View functions relating to searching for users.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
import operator

from zope import component
from zope import interface
from zope.mimetype import interfaces as zmime_interfaces

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

@view_config( route_name='search.users',
			  renderer='rest',
			  permission=nauth.ACT_SEARCH,
			  request_method='GET' )
class _UserSearchView(object):
	"""
	.. note:: This is extremely inefficient.

	.. note:: Policies need to be applied to this. For example, one policy
		is that we should only be able to find users that intersect the set of communities
		we are in. (To do that efficiently, we need community indexes).
	"""

	def __init__(self,request):
		self.request = request
		self.dataserver = self.request.registry.getUtility(nti_interfaces.IDataserver)

	def __call__(self):
		remote_user = users.User.get_user( sec.authenticated_userid( self.request ), dataserver=self.dataserver )
		partialMatch = self.request.matchdict['term']
		partialMatch = unicode(partialMatch or '').lower()
		# We tend to use this API as a user-resolution service, so
		# optimize for that case--avoid waking all other users up
		result = []

		if partialMatch and remote_user:
			# NOTE3: We have now stopped allowing this to work for user resolution.
			# This will probably break many assumptions in the UI about what and when usernames
			# can be resolved
			# NOTE2: Going through this API lets some private objects be found
			# (DynamicFriendsLists, specifically). We should probably lock that down
			result = _authenticated_search( self.request, remote_user, self.dataserver, partialMatch )


		return _format_result( result, remote_user, self.dataserver )

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
	partialMatch = request.matchdict['term']
	partialMatch = unicode(partialMatch or '').lower()
	entity = None

	if not partialMatch:
		pass
	elif users.Entity.get_entity( partialMatch ):
		# NOTE3: We have not stopped allowing this to work for user resolution.
		# This will probably break many assumptions in the UI about what and when usernames
		# can be resolved
		entity = users.Entity.get_entity( partialMatch )
		# NOTE2: Going through this API lets some private objects be found
		# (DynamicFriendsLists, specifically). We should probably lock that down
	else:
		scoped = _search_scope_to_remote_user( remote_user, partialMatch, operator.eq )
		if scoped:
			entity = scoped[0]

	result = []
	if entity is not None:
		if _make_visibility_test( remote_user )(entity):
			result.append( entity )

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

def _authenticated_search( request, remote_user, dataserver, search_term ):
	result = []
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder
	user_search_matcher = site_policies.queryAdapterInSite( remote_user, IUserSearchMatcher, request=request, default=NoOpUserSearchMatcher() )
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
		# TODO how expensive is it to actually look inside all these
		# objects?  This almost certainly wakes them up?
		# Our class name is UserMatchingGet, but we actually
		# search across all entities, like Communities

		if search_term in entity_name.lower():
			entity = users.Entity.get_entity( entity_name, dataserver=dataserver )
		else:
			entity = user_search_matcher.matches( search_term, entity_name )

		if entity is not None:
			result.append( entity )

	result.extend( _search_scope_to_remote_user( remote_user, search_term ) )

	# FIXME: Hack in a policy of limiting searching to overlapping communities
	test = _make_visibility_test( remote_user )
	# Filter to things that share a common community
	result = {x for x in result if test(x)} # ensure a set

	return result

def _search_scope_to_remote_user( remote_user, search_term, op=operator.contains ):
	result = []
	# Given a remote user, add matching friends lists, too
	for fl in remote_user.friendsLists.values():
		if not isinstance( fl, users.Entity ): # pragma: no cover
			continue
		names = user_interfaces.IFriendlyNamed( fl )
		if op( fl.username.lower(), search_term ) \
		   or op( (names.realname or '').lower(), search_term ) \
		   or op( (names.alias or '').lower(), search_term ):
			result.append( fl )
	# Also add enrolled classes
	# TODO: What about instructors?
	enrolled_sections = component.getAdapter( remote_user, app_interfaces.IContainerCollection, name='EnrolledClassSections' )
	for section in enrolled_sections.container:
		# TODO: We really want to be searching the class as well, but
		# we cannot get there from here
		if op( section.ID.lower(), search_term ) or op( section.Description.lower(), search_term ):
			result.append( section )

	if not result:
		warnings.warn( "Hack for UI: looking at display names of communities" )
		for x in remote_user.communities:
			x = users.Entity.get_entity( x )
			if x and op( x.username.lower(), search_term.lower() ):
				result.append( x )
				break

	return result


def _make_visibility_test(remote_user):
	if remote_user:
		remote_com_names = remote_user.communities - set( ('Everyone',) )
		def test(x):
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
			return not hasattr(x, 'communities') or x.communities.intersection( remote_com_names )
		return test
	return lambda x: True

class IUserSearchMatcher(interface.Interface):

	def matches( search_term, entity_name ):
		"""
		Determine if the entity matches.
		:return: The entity object, if it matched. Otherwise None.
		"""

@interface.implementer(IUserSearchMatcher)
class ComprehensiveUserSearchMatcher(object):

	def __init__( self, context=None ):
		pass

	def matches( self, search_term, entity_name ):
		entity = users.Entity.get_entity( entity_name )
		if entity:
			names = user_interfaces.IFriendlyNamed( entity )
			if search_term in (names.realname or '').lower() or search_term in (names.alias or '').lower():
				return entity


@interface.implementer(IUserSearchMatcher)
class NoOpUserSearchMatcher(object):

	def __init__( self, context=None ):
		pass

	def matches( self, search_term, entity_name ):
		return None
