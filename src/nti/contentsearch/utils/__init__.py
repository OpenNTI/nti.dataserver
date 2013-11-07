# -*- coding: utf-8 -*-
"""
Content search utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.generations.utility import findObjectsMatching
from zope.generations.utility import findObjectsProviding

from nti.chatserver import interfaces as chat_interfaces

from nti.contentsearch import common
from nti.contentsearch import discriminators
from nti.contentsearch import get_ugd_indexable_types
from nti.contentsearch import interfaces as search_interfaces

from nti.dataserver import users
from nti.deprecated import deprecated
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as forum_interfaces

from nti.externalization.oids import to_external_ntiid_oid

def find_user_dfls(user):
	"""
	Return a generator with dfl objects for the specfied user
	"""
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

def find_all_indexable_pairs(entity, condition=None):
	"""
	Return a generator with all the objects that need to be indexed.
	The genertor yield pairs (entity, obj) indicating that the object has to be indexed
	for the particuluar entity
	"""

	seen = set()
	if condition is None:
		def f(x):
			return 	nti_interfaces.IModeledContent.providedBy(x) or \
					forum_interfaces.IHeadlineTopic.providedBy(x) or \
					forum_interfaces.IPost.providedBy(x)
		condition = f

	indexable_types = get_ugd_indexable_types()
	for obj in findObjectsMatching(entity, condition):

		if forum_interfaces.IHeadlineTopic.providedBy(obj):
			obj = obj.headline

		if common.get_type_name(obj) in indexable_types:
			oid = to_external_ntiid_oid(obj)
			if oid in seen:
				continue
			seen.add(oid)

			yield (user, obj)

			# check if object is shared
			for shared_with in get_flattenedSharingTargets(obj):
				if shared_with and shared_with != user:
					yield (shared_with, obj)

def post_predicate():
	condition = lambda x : forum_interfaces.IPost.providedBy(x) or \
						   forum_interfaces.IHeadlineTopic.providedBy(x)
	return condition

def find_all_posts(user):
	return find_all_indexable_pairs(user, post_predicate())

def redaction_predicate():
	condition = lambda x : nti_interfaces.IRedaction.providedBy(x)
	return condition

def find_all_redactions(user):
	return find_all_indexable_pairs(user, redaction_predicate())

def note_predicate():
	condition = lambda x : nti_interfaces.INote.providedBy(x)
	return condition

def find_all_notes(user):
	return find_all_indexable_pairs(user, note_predicate())

def highlight_predicate():
	condition = lambda x : nti_interfaces.IHighlight.providedBy(x) and not \
						   nti_interfaces.INote.providedBy(x)
	return condition

def find_all_highlights(user):
	return find_all_indexable_pairs(user, highlight_predicate())

def messageinfo_predicate():
	condition = lambda x : chat_interfaces.IMessageInfo.providedBy(x)
	return condition

def find_all_messageinfo(user):
	return find_all_indexable_pairs(user, messageinfo_predicate())
