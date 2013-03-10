# -*- coding: utf-8 -*-
"""
Content search utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zope.intid
from zope import component
from zope.generations.utility import findObjectsProviding

from nti.deprecated import deprecated
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as forum_interfaces

from .. import get_indexable_types
from ..common import get_type_name
from .. import interfaces as search_interfaces

def get_uid(obj, intids=None):
	intids = intids or component.getUtility( zope.intid.IIntIds )
	result = intids.queryId(obj)
	return result

def find_user_dfls(user):
	"""return a generator with dfl objects for the specfied user"""

	if hasattr(user, "friendsLists"):
		source = user.friendsLists.values()
	else:
		source = findObjectsProviding(user, nti_interfaces.IFriendsList)

	for obj in source:
		if nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(obj):
			yield obj

def get_flattenedSharingTargets(context):
	"""
	Return the entities the object is shared with, including :class:`.IDynamicSharingTargetFriendsList`
	objects.
	"""
	resolver = search_interfaces.IShareableContentResolver( context, None )
	if resolver:
		return resolver.get_flattenedSharingTargets()
	return ()

@deprecated(replacement=get_flattenedSharingTargets)
def get_sharedWith(obj):
	"""
	Return the usernames the specified object is shared with.
	Deprecated as the usernames are not globally unique or resolvable.
	"""
	rsr = search_interfaces.IShareableContentResolver(obj, None)
	result = rsr.get_sharedWith() if rsr is not None else ()
	return result or ()


def find_all_indexable_pairs(user, user_get=users.Entity.get_entity, include_dfls=False, _providing=nti_interfaces.IModeledContent):
	"""
	return a generator with all the objects that need to be indexed.
	The genertor yield pairs (entity, obj) indicating that the object has to be indexed
	for the particuluar entity
	"""

	indexable_types = get_indexable_types()
	for obj in findObjectsProviding( user, _providing ):
		if get_type_name(obj) in indexable_types:
			yield (user, obj)

			# check if object is shared
			for shared_with in get_flattenedSharingTargets( obj ):
				if shared_with and shared_with != user:
					if nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( shared_with ):
						if include_dfls:
							yield (shared_with, obj)
					else:
						yield (shared_with, obj)

def find_all_posts(user, user_get=users.Entity.get_entity):
	return find_all_indexable_pairs( user, include_dfls=False, _providing=forum_interfaces.IPost)
