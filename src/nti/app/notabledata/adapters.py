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
from zope.annotation.interfaces import IAnnotations

from BTrees.OOBTree import Set

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.base.abstract_views import make_sharing_security_check

from .interfaces import IUserNotableData
from .interfaces import IUserNotableDataStorage
from .interfaces import IUserPresentationPriorityCreators

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.utils.property import CachedProperty
from nti.utils.property import annotation_alias

from nti.dataserver.metadata_index import IX_TOPICS
from nti.dataserver.metadata_index import IX_TAGGEDTO
from nti.dataserver.metadata_index import TP_TOP_LEVEL_CONTENT
from nti.dataserver.metadata_index import TP_DELETED_PLACEHOLDER
from nti.dataserver.metadata_index import CATALOG_NAME as METADATA_CATALOG_NAME

from nti.dataserver.authentication import _dynamic_memberships_that_participate_in_security

from zope.catalog.catalog import ResultSet
from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from nti.externalization.oids import to_external_ntiid_oid

_BLOG_COMMENT_MIMETYPE = "application/vnd.nextthought.forums.personalblogcomment"
_BLOG_ENTRY_MIMETYPE = "application/vnd.nextthought.forums.personalblogentry"

_BLOG_ENTRY_NTIID = "tag:nextthought.com,2011-10:%s-Topic:PersonalBlogEntry"

_TOPIC_MIMETYPE = "application/vnd.nextthought.forums.communityheadlinetopic"
_TOPIC_COMMENT_MYMETYPE = "application/vnd.nextthought.forums.generalforumcomment"

NULL_TIMERANGE = (None, None)

@interface.implementer(IUserNotableData)
@component.adapter(IUser,interface.Interface)
class UserNotableData(AbstractAuthenticatedView):

	def __init__(self, context, request):
		AbstractAuthenticatedView.__init__(self, request)
		self.remoteUser = context
		self._time_range = NULL_TIMERANGE

	def __reduce__(self):
		raise TypeError()

	@CachedProperty
	def _intids(self):
		return component.getUtility(IIntIds)
	
	@classmethod
	def get_intids(cls, intids=None):
		intids = component.getUtility(IIntIds) if intids is None else intids
		return intids
	
	@CachedProperty
	def _catalog(self):
		return component.getUtility(ICatalog, METADATA_CATALOG_NAME)

	@classmethod
	def get_notable_storage(cls, remoteUser):
		return IUserNotableDataStorage(remoteUser)
	
	@CachedProperty
	def _notable_storage(self):
		return IUserNotableDataStorage(self.remoteUser)

	@classmethod
	def get_catalog(cls, catalog=None):
		catalog = 	component.getUtility(ICatalog, METADATA_CATALOG_NAME) \
					if catalog is None else catalog
		return catalog
	
	@classmethod
	def compute_find_blog_comment_intids(cls, remoteUser, catalog=None):
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
		min_ntiid = _BLOG_ENTRY_NTIID % remoteUser.username
		# the . character is the next one after the -
		max_ntiid = min_ntiid + '.'

		catalog = cls.get_catalog(catalog)
		container_id_idx = catalog['containerId']
		docids = container_id_idx.apply({'between': (min_ntiid, max_ntiid)})
		container_ids = {container_id_idx.documents_to_values[x] for x in docids}
		result = container_id_idx.apply({'any_of': container_ids})
		return result

	def __find_blog_comment_intids(self):
		result = self.compute_find_blog_comment_intids(self.remoteUser, self._catalog)
		return result

	@classmethod
	def compute_blog_comment_intids(cls, catalog=None):
		catalog = cls.get_catalog(catalog)
		result = catalog['mimeType'].apply( {'any_of': (_BLOG_COMMENT_MIMETYPE,)} )
		return result
	
	@CachedProperty
	def _all_blog_comment_intids(self):
		result = self.compute_blog_comment_intids(self._catalog)
		return result

	@classmethod
	def compute_topics_created_by_me_intids(cls, remoteUser, catalog=None):
		catalog = cls.get_catalog(catalog)
		topic_intids = catalog['mimeType'].apply({'any_of': (_TOPIC_MIMETYPE,)})
		intids_by_me = cls.compute_intids_created_by_me(remoteUser, catalog)
		topics_created_by_me_intids = catalog.family.IF.intersection(topic_intids,
																	 intids_by_me)
		return topics_created_by_me_intids
	
	@CachedProperty
	def _topics_created_by_me_intids(self):
		result = self.compute_topics_created_by_me_intids(self.remoteUser, self._catalog)
		return result

	@classmethod
	def compute_topic_ntiids(cls, remoteUser, excluded_topic_oids=(),
							 catalog=None, intids=None):
		intids = cls.get_intids(intids)
		topic_ntiids = {
			x.NTIID or None for x in ResultSet(cls.compute_topics_created_by_me_intids(remoteUser, catalog), intids)
			if to_external_ntiid_oid(x) not in excluded_topic_oids
		}
		topic_ntiids.discard(None)
		result = list(topic_ntiids)
		return result
	
	def __topic_ntiids(self, excluded_topic_oids=()):
		result = self.compute_topic_ntiids(self.remoteUser, excluded_topic_oids,
										   self._catalog, self._intids)
		return result

	@classmethod
	def compute_all_comments_in_my_topics_intids(cls, remoteUser, excluded_topic_oids=(), 
												 catalog=None, intids=None):
		# Note that we're not doing a join to the Mime index, as only comments
		# should have this as a container id.
		__topic_ntiids = cls.compute_topic_ntiids(remoteUser, excluded_topic_oids,
												  catalog, intids)
		comments_in_my_topics_intids = catalog['containerId'].apply({'any_of': __topic_ntiids})
		return comments_in_my_topics_intids
	
	@CachedProperty
	def _all_comments_in_my_topics_intids(self):
		result = self.compute_all_comments_in_my_topics_intids(self.remoteUser, (), 
															   self._catalog, self._intids)
		return result

	@classmethod
	def compute_only_included_comments_in_my_topics_intids(cls, remoteUser, catalog=None,
														   intids=None):
		excluded_topic_oids = cls.get_not_notable_oids(remoteUser) or ()
		if not excluded_topic_oids:
			result = cls.compute_all_comments_in_my_topics_intids(remoteUser, (), 
																  catalog, intids)
			return result

		topic_ntiids = cls.compute_topic_ntiids(remoteUser, excluded_topic_oids, 
												catalog, intids)
		result = catalog['containerId'].apply({'any_of': topic_ntiids})
		return result
	
	@CachedProperty
	def _only_included_comments_in_my_topics_intids(self):
		result = self.compute_only_included_comments_in_my_topics_intids(self.remoteUser, 
																		 self._catalog, 
																		 self._intids)
		return result

	@classmethod
	def compute_find_generalForum_comment_intids(cls, remoteUser, catalog=None,
												 intids=None):
		result = cls.compute_only_included_comments_in_my_topics_intids(cls, remoteUser, 
																		catalog=None,
																		intids=None)
		return result
	
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

	@classmethod
	def compute_topic_comment_intids_to_exclude(cls, remoteUser, catalog=None, 
												intids=None):
		all_comments = cls.compute_all_comments_in_my_topics_intids(remoteUser, (), 
																	catalog, intids)
		included_comments =  \
			cls.compute_only_included_comments_in_my_topics_intids(	remoteUser, 
																	catalog,
																	intids)
		# Everything that's in all_comments, but not in included_comments
		comments_i_dont_want = catalog.family.IF.difference(all_comments, 
															included_comments)
		return comments_i_dont_want
	
	@CachedProperty
	def _topic_comment_intids_to_exclude(self):
		result = self.compute_topic_comment_intids_to_exclude(self.remoteUser, 
															  self._catalog, 
															  self._intids)
		return result

	@classmethod
	def compute_intids_created_by_me(cls, remoteUser, catalog=None):
		catalog = cls.get_catalog(catalog)
		result = catalog['creator'].apply({'any_of': (remoteUser.username,)})
		return result
	
	@CachedProperty
	def _intids_created_by_me(self):
		result = self.compute_intids_created_by_me(self.remoteUser, self._catalog)
		return result

	@classmethod
	def compute_intids_in_time_range(cls, time_range=NULL_TIMERANGE, catalog=None):
		catalog = cls.get_catalog(catalog)
		min_created_time, max_created_time = time_range
		if min_created_time is None and max_created_time is None:
			return None
		intids_in_time_range = catalog['createdTime'].apply({'between': (min_created_time, max_created_time,)})
		return intids_in_time_range
	
	@CachedProperty('_time_range')
	def _intids_in_time_range(self):
		result = self.compute_intids_in_time_range(self._time_range, self._catalog)
		return result

	@classmethod
	def compute_safely_viewable_notable_intids(	cls, remoteUser, time_range=NULL_TIMERANGE, 
												catalog=None, intids=None):
		catalog = cls.get_catalog(catalog)
		intids_shared_to_me = catalog['sharedWith'].apply({'all_of': (remoteUser.username,)})

		toplevel_intids_extent = catalog[IX_TOPICS][TP_TOP_LEVEL_CONTENT].getExtent()
		toplevel_intids_shared_to_me = toplevel_intids_extent.intersection(intids_shared_to_me)

		intids_replied_to_me = catalog['repliesToCreator'].apply({'any_of': (remoteUser.username,)})

		intids_blog_comments = cls.compute_find_blog_comment_intids(remoteUser, catalog)
		toplevel_intids_blog_comments = toplevel_intids_extent.intersection(intids_blog_comments)

		blogentry_intids = catalog['mimeType'].apply({'any_of': (_BLOG_ENTRY_MIMETYPE,)})
		blogentry_intids_shared_to_me = catalog.family.IF.intersection(intids_shared_to_me, blogentry_intids)

		toplevel_intids_forum_comments = \
			cls.compute_only_included_comments_in_my_topics_intids(remoteUser, catalog, intids)

		safely_viewable_intids = [toplevel_intids_shared_to_me,
								  intids_replied_to_me,
								  toplevel_intids_blog_comments,
								  blogentry_intids_shared_to_me,
								  toplevel_intids_forum_comments]

		_notable_storage = cls.get_notable_storage(remoteUser)
		_notable_storage.add_intids(safely_viewable_intids, safe=True)

		safely_viewable_intids = catalog.family.IF.multiunion(safely_viewable_intids)
		_intids_in_time_range = cls.compute_intids_in_time_range(time_range, catalog)
		if _intids_in_time_range is not None:
			safely_viewable_intids = catalog.family.IF.intersection(_intids_in_time_range,
																	safely_viewable_intids)

		# Subtract any comments that crept in that I don't want
		_topic_comment_intids_to_exclude = \
				cls.compute_topic_comment_intids_to_exclude(remoteUser, catalog, intids)
		safely_viewable_intids = catalog.family.IF.difference(safely_viewable_intids,
															  _topic_comment_intids_to_exclude)
		return safely_viewable_intids
	
	@CachedProperty('_time_range')
	def _safely_viewable_notable_intids(self):
		result = self.compute_safely_viewable_notable_intids(self.remoteUser, 
															 self._time_range,
															 self._catalog,
															 self._intids)
		return result

	@classmethod
	def compute_notable_intids(cls, request, remoteUser, time_range=NULL_TIMERANGE,
							   catalog=None, intids=None):
		# TODO: See about optimizing this query plan. ZCatalog has a
		# CatalogPlanner object that we might could use.
		intids = cls.get_intids(intids)
		catalog = cls.get_catalog(catalog)
		toplevel_intids_extent = catalog[IX_TOPICS][TP_TOP_LEVEL_CONTENT].getExtent()
		deleted_intids_extent = catalog[IX_TOPICS][TP_DELETED_PLACEHOLDER].getExtent()

		# Things tagged to me or my security-aware dynamic memberships
		# XXX: This is probably slow? How many unions does this wind up doing?
		# it definitely slows down over time
		tagged_to_usernames_or_intids = {remoteUser.username}
		# Note the use of private API, a signal to cleanup soon
		for membership in _dynamic_memberships_that_participate_in_security(remoteUser, as_principals=False ):
			if IDynamicSharingTargetFriendsList.providedBy(membership):
				tagged_to_usernames_or_intids.add( membership.NTIID )
		intids_tagged_to_me = catalog[IX_TAGGEDTO].apply({'any_of': tagged_to_usernames_or_intids})

		safely_viewable_intids = cls.compute_safely_viewable_notable_intids(remoteUser,
																			time_range, 
																			catalog, 
																			intids)

		important_creator_usernames = set()
		for provider in component.subscribers( (remoteUser, request),
											   IUserPresentationPriorityCreators ):
			important_creator_usernames.update( provider.iter_priority_creator_usernames() )

		intids_by_priority_creators = catalog['creator'].apply({'any_of': important_creator_usernames})

		# Top-level things by the instructors...
		toplevel_intids_by_priority_creators = \
				toplevel_intids_extent.intersection(intids_by_priority_creators)
		# ...taking out blog comments because that might be confusing
		# (2014-06-10)
		_all_blog_comment_intids = cls.compute_blog_comment_intids(catalog)
		toplevel_intids_by_priority_creators =  \
			catalog.family.IF.difference(toplevel_intids_by_priority_creators,
										_all_blog_comment_intids)

		# As-of fall 2014, auto-created topics are not created by the instuctor,
		# but instead a separate entity, so we want to return those too. In the past,
		# they were created by the instructor, which means that if you go far enough
		# back in notable data you'll find them (and at the time they were created, we
		# were explicitly excluding them)---but the benefit to knowing about new discussions
		# from the instructors outweighs any oddity from the old stuff.

		# Now any topics by our a-listers, but only non-excluded topics
		topic_intids = catalog['mimeType'].apply({'any_of': (_TOPIC_MIMETYPE,)})
		topic_intids_by_priority_creators = \
				catalog.family.IF.intersection(	topic_intids,
		 										intids_by_priority_creators)

		# Sadly, to be able to provide the "TotalItemCount" we have to
		# apply security to all the intids not guaranteed to be
		# viewable; if we didn't have to do that we could imagine
		# doing so incrementally, as needed, on the theory that there
		# are probably more things shared directly with me or replied
		# to me than created by others that I happen to be able to see
		questionable_intids = [toplevel_intids_by_priority_creators,
							   intids_tagged_to_me,
							   topic_intids_by_priority_creators,
						   ]
		
		_notable_storage = cls.get_notable_storage(remoteUser)
		_notable_storage.add_intids(questionable_intids,safe=False)
		questionable_intids = catalog.family.IF.multiunion(	questionable_intids )
		
		_intids_in_time_range = cls.compute_intids_in_time_range(time_range, catalog)
		if _intids_in_time_range is not None:
			questionable_intids = catalog.family.IF.intersection(_intids_in_time_range,
																 questionable_intids)


		uidutil = intids
		security_check = make_sharing_security_check(request, remoteUser)
		for questionable_uid in questionable_intids:
			if questionable_uid in safely_viewable_intids:
				continue
			questionable_obj = uidutil.getObject(questionable_uid)
			if security_check(questionable_obj):
				safely_viewable_intids.add(questionable_uid)

		# Make sure none of the stuff we created got in
		intids_created_by_me = cls.compute_intids_created_by_me(remoteUser, catalog)
		safely_viewable_intids = catalog.family.IF.difference(safely_viewable_intids,
															  intids_created_by_me)

		# Make sure nothing that's deleted got in
		non_deleted_safely_viewable_intids = safely_viewable_intids - deleted_intids_extent
		return non_deleted_safely_viewable_intids
	
	@CachedProperty('_time_range')
	def _notable_intids(self):
		result = self.compute_notable_intids(self.request, self.remoteUser, 
											 self._time_range,
											 self._catalog, 
											 self._intids)
		return result

	@classmethod
	def return_notable_intids(cls, request, remoteUser,
							  min_created_time=None,
							  max_created_time=None,
							  catalog=None, intids=None):
		time_range = (min_created_time, max_created_time)
		result = cls.compute_notable_intids(request,
											remoteUser, 
											time_range,
											catalog, 
											intids)
		return result
	
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

	@classmethod
	def do_sort_notable_intids(cls, notable_intids,
							   field_name='createdTime',
							   limit=None,
							   reverse=False,
							   reify=False,
							   catalog=None):
		catalog = cls.get_catalog(catalog)
		
		# Sorting returns a generator which is fine unless we need to get a length.
		# In many cases we don't so we let the caller decide
		_sorted = catalog[field_name].sort(notable_intids,
										   limit=limit,
										   reverse=reverse)
		if not reify:
			return _sorted

		# For large lists, an array is more memory efficient then a list,
		# since it uses native storage
		array_type = 'l' if isinstance(catalog.family.maxint, long) else 'i' # Py3 porting issue, long went away?
		return array(str(array_type), _sorted)
	
	def sort_notable_intids(self, notable_intids,
							field_name='createdTime',
							limit=None,
							reverse=False,
							reify=False):
		
		result = self.do_sort_notable_intids(notable_intids, 
											 field_name=field_name,
											 limit=limit,
											 reverse=reverse,
											 reify=reify,
											 catalog=self._catalog)
		return result

	@classmethod
	def do_iter_notable_intids(cls, notable_intids, ignore_missing=False, intids=None):
		intids = cls.get_intids(intids)
		factory = _SafeResultSet if ignore_missing else ResultSet
		return factory(notable_intids, intids)
	
	def iter_notable_intids(self, notable_intids, ignore_missing=False):
		result  = self.do_iter_notable_intids(notable_intids,
											  ignore_missing,
											  self._intids)
		return result

	_KEY = 'nti.appserver.ugd_query_views._NotableUGDLastViewed'
	lastViewed = annotation_alias(_KEY, annotation_property='remoteUser', default=0,
								  doc="LastViewed is stored as an annotation on the user")

	@classmethod
	def get_notable_lastViewed(cls, remoteUser):
		annotations =  IAnnotations(remoteUser, {})
		result = annotations.get(cls._KEY, None)
		return result
	
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

	@classmethod
	def get_not_notable_oids(cls, remoteUser):
		annotations =  IAnnotations(remoteUser, {})
		result = annotations.get(cls._NKEY, None)
		return result
		
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

from zope import lifecycleevent
from zope.container.contained import Contained
from zope.annotation.factory import factory as an_factory

from persistent import Persistent
from persistent.list import PersistentList

from nti.utils.property import Lazy

@interface.implementer(IUserNotableDataStorage)
@component.adapter(IUser)
class UserNotableDataStorage(Persistent,Contained):

	def __init__(self):
		pass

	@property
	def context(self):
		return self.__parent__

	@Lazy
	def _safe_intid_set(self):
		self._p_changed = True
		return self.context.family.IF.TreeSet()

	@Lazy
	def _unsafe_intid_set(self):
		self._p_changed = True
		return self.context.family.IF.TreeSet()

	@Lazy
	def _owned_objects(self):
		self._p_changed = True
		# We don't ever expect this to be very big
		return PersistentList()

	# Migration compatibility
	def values(self):
		if '_owned_objects' in self.__dict__:
			return self._owned_objects
		return ()

	def store_intid(self, intid, safe=False):
		s = self._safe_intid_set if safe else self._unsafe_intid_set

		added = s.add(intid)
		if added:
			return intid

	def store_object(self, obj, safe=False, take_ownership=False):
		# Note we directly access the intid attribute
		if take_ownership:
			if getattr(obj, '_ds_intid', None) is not None:
				# Programming error...somebody lost track of ownership
				raise ValueError("Object already registered")
			lifecycleevent.created(obj)
			assert getattr(obj, '_ds_intid', None) is None
			self._owned_objects.append(obj)
			if getattr(obj, '__parent__', None) is None:
				obj.__parent__ = self
			lifecycleevent.added(obj, self, str(len(self._owned_objects)))

		if getattr(obj, '_ds_intid', None) is None:
			raise ValueError("Object does not have intid")
		return self.store_intid(getattr(obj, '_ds_intid'), safe=safe)

	def add_intids(self, ids, safe=False):
		"""
		If we have intids for the given safety level, append them
		to the array. Optimization for the common case where
		we don't have one or the other to avoid creating expensive
		Set objects.
		"""
		self._p_activate()
		s = '_safe_intid_set' if safe else '_unsafe_intid_set'
		if s in self.__dict__: # has Lazy kicked in?
			ids.append( getattr(self, s) )

UserNotableDataStorageFactory = an_factory(UserNotableDataStorage)
