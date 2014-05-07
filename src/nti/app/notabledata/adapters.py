#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from array import array

from zope import interface
from zope import component

from BTrees.OOBTree import Set

from .interfaces import IUserNotableData
from .interfaces import IUserPresentationPriorityCreators
from nti.dataserver.interfaces import IUser

from nti.utils.property import CachedProperty
from nti.utils.property import annotation_alias

from nti.dataserver.metadata_index import CATALOG_NAME as METADATA_CATALOG_NAME
from zope.catalog.interfaces import ICatalog
from zope.catalog.catalog import ResultSet

from zope.intid.interfaces import IIntIds

from nti.externalization.oids import to_external_ntiid_oid

from nti.app.base.abstract_views import AbstractAuthenticatedView

_BLOG_COMMENT_MIMETYPE = "application/vnd.nextthought.forums.personalblogcomment"
_BLOG_ENTRY_MIMETYPE = "application/vnd.nextthought.forums.personalblogentry"

_BLOG_ENTRY_NTIID = "tag:nextthought.com,2011-10:%s-Topic:PersonalBlogEntry"

_TOPIC_MIMETYPE = "application/vnd.nextthought.forums.communityheadlinetopic"
_TOPIC_COMMENT_MYMETYPE = "application/vnd.nextthought.forums.generalforumcomment"

@interface.implementer(IUserNotableData)
@component.adapter(IUser,interface.Interface)
class UserNotableData(AbstractAuthenticatedView):

	def __init__(self, context, request):
		AbstractAuthenticatedView.__init__(self, request)
		self.remoteUser = context
		self._time_range = (None,None)

	def __reduce__(self):
		raise TypeError()

	@CachedProperty
	def _intids(self):
		return component.getUtility(IIntIds)


	@CachedProperty
	def _catalog(self):
		return component.getUtility(ICatalog, METADATA_CATALOG_NAME)

	def __find_blog_comment_intids(self):
		# We know that blog comments have a container ID that is the
		# blog entry's NTIID. We know that the blog entry's NTIID is deterministic
		# and boundable (we know the beginning and we can put an entry
		# that is exactly after the last possible NTIID we would generate, and
		# yet still before any other NTIID we would generate). So we first get all
		# the blog NTIIDs, then we find things that use them as containers and which
		# are comments (actually, we skip that last step; we know the only things
		# that can be contained are the headline post and comments, and the headline
		# post will be filtered out automatically because we created it).

		# The base ntiid. Real ntiids will start with this, followed by a -
		min_ntiid = _BLOG_ENTRY_NTIID % self.remoteUser.username
		# the . character is the next one after the -
		max_ntiid = min_ntiid + '.'

		container_id_idx = self._catalog['containerId']
		docids = container_id_idx.apply({'between': (min_ntiid, max_ntiid)})
		container_ids = {container_id_idx.documents_to_values[x] for x in docids}

		return container_id_idx.apply({'any_of': container_ids})

	@CachedProperty
	def _topics_created_by_me_intids(self):
		catalog = self._catalog
		topic_intids = catalog['mimeType'].apply({'any_of': (_TOPIC_MIMETYPE,)})

		topics_created_by_me_intids = catalog.family.IF.intersection(topic_intids,
																	 self._intids_created_by_me)
		return topics_created_by_me_intids

	def __topic_ntiids(self, excluded_topic_oids=()):
		topic_ntiids = [x.NTIID for x in ResultSet(self._topics_created_by_me_intids, self._intids)
						if to_external_ntiid_oid(x) not in excluded_topic_oids]

		return topic_ntiids

	@CachedProperty
	def _all_comments_in_my_topics_intids(self):
		# Note that we're not doing a join to the Mime index, as only comments
		# should have this as a container id.
		comments_in_my_topics_intids = self._catalog['containerId'].apply({'any_of': self.__topic_ntiids()})
		return comments_in_my_topics_intids

	@CachedProperty
	def _only_included_comments_in_my_topics_intids(self):
		excluded_topic_oids = self._not_notable_oids or ()
		if not excluded_topic_oids:
			return self._all_comments_in_my_topics_intids

		return self._catalog['containerId'].apply({'any_of': self.__topic_ntiids(excluded_topic_oids)})

	def __find_generalForum_comment_intids(self):
		# Get the toplevel intids of comments created in a forum
		# that I own (created). There is not a very good way to do this,
		# sadly. Indexing NTIID is a poor choice because it's 1-to-1
		# The best we can seem to do is find all the forums I created,
		# manually get their NTIIDs,  get things that are in those containers
		# that are toplevel.
		# Once we do this, though, we mist still subtract things shared directly
		# to me that are in _all_comments_in_my_topics_intids but not in this
		# set, because of the way ACL sharing for community topics is implemented
		# (the instructor is explicitly in the sharingTargets list)
		return self._only_included_comments_in_my_topics_intids

	@CachedProperty
	def _topic_comment_intids_to_exclude(self):
		all_comments = self._all_comments_in_my_topics_intids
		included_comments = self._only_included_comments_in_my_topics_intids

		# Everything that's in all_comments, but not in included_comments
		comments_i_dont_want = self._catalog.family.IF.difference(all_comments, included_comments)
		return comments_i_dont_want

	@CachedProperty
	def _intids_created_by_me(self):
		return self._catalog['creator'].apply({'any_of': (self.remoteUser.username,)})

	@CachedProperty('_time_range')
	def _intids_in_time_range(self):
		min_created_time, max_created_time = self._time_range
		if min_created_time is None and max_created_time is None:
			return None

		intids_in_time_range = self._catalog['createdTime'].apply({'between': (min_created_time, max_created_time,)})
		return intids_in_time_range

	@CachedProperty('_time_range')
	def _safely_viewable_notable_intids(self):
		catalog = self._catalog
		intids_shared_to_me = catalog['sharedWith'].apply({'all_of': (self.remoteUser.username,)})

		toplevel_intids_extent = catalog['topics']['topLevelContent'].getExtent()
		toplevel_intids_shared_to_me = toplevel_intids_extent.intersection(intids_shared_to_me)

		intids_replied_to_me = catalog['repliesToCreator'].apply({'any_of': (self.remoteUser.username,)})

		intids_blog_comments = self.__find_blog_comment_intids()
		toplevel_intids_blog_comments = toplevel_intids_extent.intersection(intids_blog_comments)

		blogentry_intids = catalog['mimeType'].apply({'any_of': (_BLOG_ENTRY_MIMETYPE,)})
		blogentry_intids_shared_to_me = catalog.family.IF.intersection(intids_shared_to_me, blogentry_intids)

		toplevel_intids_forum_comments = self.__find_generalForum_comment_intids()

		# We use low-level optimization to get this next one; otherwise
		# we'd need some more indexes to make it efficient
		intids_of_my_circled_events = self.remoteUser._circled_events_intids_storage

		safely_viewable_intids = catalog.family.IF.multiunion((toplevel_intids_shared_to_me,
															   intids_replied_to_me,
															   intids_of_my_circled_events,
															   toplevel_intids_blog_comments,
															   blogentry_intids_shared_to_me,
															   toplevel_intids_forum_comments))
		if self._intids_in_time_range is not None:
			safely_viewable_intids = catalog.family.IF.intersection(self._intids_in_time_range,
																	safely_viewable_intids)

		# Subtract any comments that crept in that I don't want
		safely_viewable_intids = catalog.family.IF.difference(safely_viewable_intids,
															  self._topic_comment_intids_to_exclude)
		return safely_viewable_intids

	@CachedProperty('_time_range')
	def _notable_intids(self):
		# TODO: See about optimizing this query plan. ZCatalog has a
		# CatalogPlanner object that we might could use.
		catalog = self._catalog
		toplevel_intids_extent = catalog['topics']['topLevelContent'].getExtent()
		intids_tagged_to_me = catalog['taggedTo'].apply({'any_of': (self.remoteUser.username,)})

		safely_viewable_intids = self._safely_viewable_notable_intids


		important_creator_usernames = set()
		for provider in component.subscribers( (self.remoteUser, self.request),
											   IUserPresentationPriorityCreators ):
			important_creator_usernames.update( provider.iter_priority_creator_usernames() )

		intids_by_priority_creators = catalog['creator'].apply({'any_of': important_creator_usernames})
		toplevel_intids_by_priority_creators = toplevel_intids_extent.intersection(intids_by_priority_creators)


		# Sadly, to be able to provide the "TotalItemCount" we have to
		# apply security to all the intids not guaranteed to be
		# viewable; if we didn't have to do that we could imagine
		# doing so incrementally, as needed, on the theory that there
		# are probably more things shared directly with me or replied
		# to me than created by others that I happen to be able to see

		questionable_intids = catalog.family.IF.union( toplevel_intids_by_priority_creators,
													   intids_tagged_to_me )
		if self._intids_in_time_range is not None:
			questionable_intids = catalog.family.IF.intersection(self._intids_in_time_range,
																 questionable_intids)


		uidutil = self._intids
		security_check = self.make_sharing_security_check()
		for questionable_uid in questionable_intids:
			if questionable_uid in safely_viewable_intids:
				continue
			questionable_obj = uidutil.getObject(questionable_uid)
			if security_check(questionable_obj):
				safely_viewable_intids.add(questionable_uid)

		# Make sure none of the stuff we created got in
		intids_created_by_me = self._intids_created_by_me
		safely_viewable_intids = catalog.family.IF.difference(safely_viewable_intids, intids_created_by_me)

		return safely_viewable_intids

	def get_notable_intids(self, min_created_time=None, max_created_time=None):
		self._time_range = (min_created_time, max_created_time)
		ids = self._notable_intids
		return ids


	def __len__(self):
		return len(self.get_notable_intids())

	def __bool__(self):
		if self._safely_viewable_notable_intids:
			return True
		return bool(len(self))
	__nonzero__ = __bool__

	def __iter__(self):
		return iter(ResultSet(self.get_notable_intids(), self._intids))

	def sort_notable_intids(self, notable_intids,
							field_name='createdTime',
							limit=None,
							reverse=False,
							reify=False):
		# Sorting returns a generator which is fine unless we need to get a length.
		# In many cases we don't so we let the caller decide
		_sorted = self._catalog[field_name].sort(notable_intids,
												 limit=limit,
												 reverse=reverse)
		if not reify:
			return _sorted

		# For large lists, an array is more memory efficient then a list,
		# since it uses native storage
		array_type = 'l' if isinstance(self._catalog.family.maxint, long) else 'i' # Py3 porting issue, long went away?
		return array(str(array_type), _sorted)

	def iter_notable_intids(self, notable_intids, ignore_missing=False):
		factory = _SafeResultSet if ignore_missing else ResultSet
		return factory(notable_intids, self._intids)

	_KEY = 'nti.appserver.ugd_query_views._NotableUGDLastViewed'
	lastViewed = annotation_alias(_KEY, annotation_property='remoteUser', default=0,
								  doc="LastViewed is stored as an annotation on the user")


	def is_object_notable(self, maybe_notable):
		# Tests with a Janux database snapshot seem to indicate that the intid
		# catalog queries are fast enough that this doesn't add much/any
		# overhead. The other end of the spectrum is to brute-force the
		# algorithm by hand.

		iid = self._intids.queryId(maybe_notable)
		if iid is None:
			return False

		notables = self._notable_intids
		return iid in notables

	_NKEY = 'nti.appserver.ugd_query_views._NotableUGD_ExcludedOIDs'
	_not_notable_oids = annotation_alias(_NKEY, annotation_property='remoteUser',
										 doc="A set of OIDs to exclude (stored on the user)"
										 "We use OID instead of intid to guard against re-use.")

	def object_is_not_notable(self, maybe_notable):
		# Right now, we only support this and check it for
		# forum objects
		if getattr(maybe_notable, 'mimeType', '') == _TOPIC_MIMETYPE:
			not_notable = self._not_notable_oids
			if not_notable is None:
				not_notable = self._not_notable_oids = Set()
			not_notable.add( to_external_ntiid_oid(maybe_notable) )

class _SafeResultSet(ResultSet):

	def __iter__(self):
		for uid in self.uids:
			obj = self.uidutil.queryObject(uid)
			if obj is not None:
				yield obj
