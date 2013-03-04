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

from nti.dataserver import users
from nti.dataserver.users import friends_lists
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
		source = findObjectsProviding( user, nti_interfaces.IFriendsList)
	
	for obj in source:
		if nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(obj):
			yield obj

def get_sharedWith(obj):
	"""return the usernames the specified obejct is shared with"""
	# from IPython.core.debugger import Tracer;  Tracer()() ## DEBUG ##
	rsr = search_interfaces.IShareableContentResolver(obj, None)
	result = rsr.get_sharedWith() if rsr is not None else ()
	return result or ()

def find_all_indexable_pairs(user, user_get=users.Entity.get_entity, include_dfls=False):
	"""
	return a generator with all the objects that need to be indexed. 
	The genertor yield pairs (entity, obj) indicating that the object has to be indexed
	for the particuluar entity
	"""

	dfls = []
	username = user.username
	
	indexable_types = get_indexable_types()
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		
		if include_dfls and nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(obj):
			dfls.append(obj)
		elif get_type_name(obj) in indexable_types:
			
			yield (user, obj)
			
			# check if object is shared 
			for uname in get_sharedWith(obj):
				sharing_user = user_get(uname)
				if sharing_user and uname != username: 
					yield (sharing_user, obj)

	for dfl in dfls:
		for container in dfl.containersOfShared.containers.values():
			for obj in container:
				if get_type_name(obj) in indexable_types:
					yield (dfl, obj)

def find_all_posts(user, user_get=users.Entity.get_entity):
	
	for obj in findObjectsProviding( user, forum_interfaces.IPost):
			
		yield (user, obj)
			
		# check if object is shared 
		for uname in get_sharedWith(obj):
			sharing_user = user_get(uname)
			if sharing_user and uname != user.username: 
				yield (sharing_user, obj)
