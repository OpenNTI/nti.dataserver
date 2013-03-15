# -*- coding: utf-8 -*-
"""
Content search utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope.generations.utility import findObjectsMatching
from zope.generations.utility import findObjectsProviding

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver import users
from nti.deprecated import deprecated
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as forum_interfaces

from nti.externalization.oids import to_external_ntiid_oid

from ..common import get_type_name
from .. import get_ugd_indexable_types
from .. import interfaces as search_interfaces
from .. import _discriminators as discriminators

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
	resolver = search_interfaces.IShareableContentResolver(context, None)
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


def find_all_indexable_pairs(user, condition=None):
	"""
	return a generator with all the objects that need to be indexed.
	The genertor yield pairs (entity, obj) indicating that the object has to be indexed
	for the particuluar entity
	"""

	seen = set()
	if condition is None:
		def f(x):
			return 	nti_interfaces.IModeledContent.providedBy(x) or \
					forum_interfaces.IHeadlineTopic.providedBy(x)
		condition = f

	indexable_types = get_ugd_indexable_types()
	for obj in findObjectsMatching(user, condition):

		if forum_interfaces.IHeadlineTopic.providedBy(obj):
			obj = obj.headline

		if get_type_name(obj) in indexable_types:
			oid = to_external_ntiid_oid(obj)
			if oid in seen:
				continue
			seen.add(oid)

			yield (user, obj)

			# check if object is shared
			for shared_with in get_flattenedSharingTargets(obj):
				if shared_with and shared_with != user:
					yield (shared_with, obj)

def find_all_posts(user):
	condition = lambda x : 	forum_interfaces.IPost.providedBy(x) or \
							forum_interfaces.IHeadlineTopic.providedBy(x)
	return find_all_indexable_pairs(user, condition)

def find_all_redactions(user):
	condition = lambda x : nti_interfaces.IRedaction.providedBy(x)
	return find_all_indexable_pairs(user, condition)

def find_all_notes(user):
	condition = lambda x : nti_interfaces.INote.providedBy(x)
	return find_all_indexable_pairs(user, condition)

def find_all_highlights(user):
	condition = lambda x : 	nti_interfaces.IHighlight.providedBy(x) and not \
							nti_interfaces.INote.providedBy(x)
	return find_all_indexable_pairs(user, condition)

def find_all_messageinfo(user):
	condition = lambda x : chat_interfaces.IMessageInfo.providedBy(x)
	return find_all_indexable_pairs(user, condition)
