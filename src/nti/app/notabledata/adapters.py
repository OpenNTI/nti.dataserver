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

from .interfaces import IUserNotableData
from .interfaces import IUserPresentationPriorityCreators
from nti.dataserver.interfaces import IUser

from nti.utils.property import CachedProperty
from nti.utils.property import annotation_alias

from nti.dataserver.metadata_index import CATALOG_NAME as METADATA_CATALOG_NAME
from zope.catalog.interfaces import ICatalog
from zope.catalog.catalog import ResultSet

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

_BLOG_COMMENT_MIMETYPE = "application/vnd.nextthought.forums.personalblogcomment"

_BLOG_ENTRY_NTIID = "tag:nextthought.com,2011-10:%s-Topic:PersonalBlogEntry"

@interface.implementer(IUserNotableData)
@component.adapter(IUser,interface.Interface)
class UserNotableData(AbstractAuthenticatedView):

	def __init__(self, context, request):
		AbstractAuthenticatedView.__init__(self, request)
		self.remoteUser = context

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
	def _safely_viewable_notable_intids(self):
		catalog = self._catalog
		intids_shared_to_me = catalog['sharedWith'].apply({'all_of': (self.remoteUser.username,)})
		toplevel_intids_extent = catalog['topics']['topLevelContent'].getExtent()
		toplevel_intids_shared_to_me = toplevel_intids_extent.intersection(intids_shared_to_me)
		intids_replied_to_me = catalog['repliesToCreator'].apply({'any_of': (self.remoteUser.username,)})

		intids_blog_comments = self.__find_blog_comment_intids()
		toplevel_intids_blog_comments = toplevel_intids_extent.intersection(intids_blog_comments)

		# We use low-level optimization to get this next one; otherwise
		# we'd need some more indexes to make it efficient
		intids_of_my_circled_events = self.remoteUser._circled_events_intids_storage

		safely_viewable_intids = catalog.family.IF.multiunion((toplevel_intids_shared_to_me,
															   intids_replied_to_me,
															   intids_of_my_circled_events,
															   toplevel_intids_blog_comments))

		return safely_viewable_intids

	@CachedProperty
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

		uidutil = self._intids
		security_check = self.make_sharing_security_check()
		for questionable_uid in questionable_intids:
			if questionable_uid in safely_viewable_intids:
				continue
			questionable_obj = uidutil.getObject(questionable_uid)
			if security_check(questionable_obj):
				safely_viewable_intids.add(questionable_uid)

		# Make sure none of the stuff we created got in
		intids_created_by_me = catalog['creator'].apply({'any_of': (self.remoteUser.username,)})
		safely_viewable_intids = catalog.family.IF.difference(safely_viewable_intids, intids_created_by_me)

		return safely_viewable_intids

	def get_notable_intids(self, max_created_time=None):
		ids = self._notable_intids
		if max_created_time is not None:
			catalog = self._catalog
			intids_in_time_range = catalog['createdTime'].apply({'between': (None, max_created_time,)})
			ids = catalog.family.IF.intersection(ids, intids_in_time_range)
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

	def iter_notable_intids(self, notable_intids):
		return ResultSet(notable_intids, self._intids)

	_KEY = 'nti.appserver.ugd_query_views._NotableUGDLastViewed'
	lastViewed = annotation_alias(_KEY, annotation_property='remoteUser', default=0,
								  doc="LastViewed is stored as an annotation on the user")
