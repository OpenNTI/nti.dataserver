from __future__ import print_function, unicode_literals

import zope.intid
from zope import component
from zope.generations.utility import findObjectsProviding

from nti.dataserver import users
from nti.dataserver.users import friends_lists
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import get_indexable_types
from nti.contentsearch.common import get_type_name
from nti.contentsearch import interfaces as search_interfaces

def get_uid(obj, intids=None):
	intids = intids or component.getUtility( zope.intid.IIntIds )
	result = intids.getId(obj)
	return result

def find_user_dfls(user):
	"""return a generator with dfl objects for the specfied user"""
	
	for obj in findObjectsProviding( user, nti_interfaces.IFriendsList):
		if isinstance(obj, friends_lists.DynamicFriendsList):
			yield obj

def get_sharedWith(obj):
	"""return the usernames the specified obejct is shared with"""
	# from IPython.core.debugger import Tracer;  Tracer()() ## DEBUG ##
	adapted = component.queryAdapter(obj, search_interfaces.IContentResolver)
	result = getattr(adapted, 'get_sharedWith', None) if adapted is not None else None
	result = result() if result else ()
	return result

def find_all_indexable_pairs(user, user_get=users.Entity.get_entity, include_dfls=True):
	"""
	return a generator with all the objects that need to be indexed. 
	The genertor yield pairs (entity, obj) indicating that the object has to be indexed
	for the particuluar entity
	"""

	dfls = []
	username = user.username
	
	#intids = intids or component.getUtility( zope.intid.IIntIds )
	
	indexable_types = get_indexable_types()
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		
		if isinstance(obj, friends_lists.DynamicFriendsList) and include_dfls:
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
				if obj is not None and get_type_name(obj) in indexable_types:
					yield (dfl, obj)
