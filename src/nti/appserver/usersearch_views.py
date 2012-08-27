#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
View functions relating to searching for users.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

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

from nti.externalization.datastructures import isSyntheticKey
from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict

import warnings

from . import interfaces as app_interfaces

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

		if not partialMatch:
			pass
		elif users.Entity.get_entity( partialMatch ):
			# NOTE: If the partial match is an exact match but also a component
			# it cannot be searched for. For example, a community named 'NextThought'
			# prevents searching for 'nextthought' if you expect to match '@nextthought.com'
			result.append( users.Entity.get_entity( partialMatch ) )
			# NOTE2: Going through this API lets some private objects be found
			# (DynamicFriendsLists, specifically). We should probably lock that down
		else:
			_users = self.dataserver.root['users']
			# Searching the userid is generally not what we want
			# now that we have username and alias (e.g,
			# tfandango@gmail.com -> Troy Daley. Search for "Dan" and get Troy and
			# be very confused.). As a compromise, we include them
			# if there are no other matches
			uid_matches = []
			for maybeMatch in _users.iterkeys():
				if isSyntheticKey( maybeMatch ):
					continue

				# TODO how expensive is it to actually look inside all these
				# objects?  This almost certainly wakes them up?
				# Our class name is UserMatchingGet, but we actually
				# search across all entities, like Communities
				userObj = users.Entity.get_entity( maybeMatch, dataserver=self.dataserver )
				if not userObj:
					continue

				if partialMatch in maybeMatch.lower():
					uid_matches.append( userObj )

				names = user_interfaces.IFriendlyNamed( userObj )
				if partialMatch in (names.realname or '').lower() \
					   or partialMatch in (names.alias or '').lower():
					result.append( userObj )

			if remote_user:
				# Given a remote user, add matching friends lists, too
				for fl in remote_user.friendsLists.values():
					if not isinstance( fl, users.Entity ):
						continue
					names = user_interfaces.IFriendlyNamed( fl )
					if partialMatch in fl.username.lower() \
					   or partialMatch in (names.realname or '').lower() \
					   or partialMatch in (names.alias or '').lower():
						result.append( fl )
				# Also add enrolled classes
				# TODO: What about instructors?
				enrolled_sections = component.getAdapter( remote_user, app_interfaces.IContainerCollection, name='EnrolledClassSections' )
				for section in enrolled_sections.container:
					# TODO: We really want to be searching the class as well, but
					# we cannot get there from here
					if partialMatch in section.ID.lower() or partialMatch in section.Description.lower():
						result.append( section )

			if uid_matches:
				result.extend(uid_matches)

			if not result:
				warnings.warn( "Hack for UI: looking at display names of communities" )
				for x in remote_user.communities:
					x = users.Entity.get_entity( x )
					if x and x.username.lower() == partialMatch.lower():
						result.append( x )
						break
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
		result.__parent__ = self.dataserver.root
		result.__name__ = 'UserSearch' # TODO: Hmm
		return result
