#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Indexing metadata about most objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable 'redefining builtin id' because
# we get that from superclass
#pylint: disable=W0622

#: The name of the utility that the Zope Catalog
#: should be registered under
CATALOG_NAME = 'nti.dataserver.++etc++metadata-catalog'

from zope import component
from zope import interface

from .interfaces import IContained as INTIContained
from .interfaces import ICreatedUsername
from .interfaces import IModeledContent
from .interfaces import IInspectableWeakThreadable
from .interfaces import IThreadable
from .interfaces import IFriendsList
from .interfaces import IDevice
from .interfaces import ILastModified
from .interfaces import IUser
from .interfaces import IDynamicSharingTargetFriendsList
from .interfaces import IUserTaggedContent
from .interfaces import IDeletedObjectPlaceholder
from .contenttypes.forums.interfaces import IHeadlinePost
from .contenttypes.forums.interfaces import ICommentPost

from zope.catalog.interfaces import ICatalog
from zope.catalog.interfaces import ICatalogIndex
from zc.intid import IIntIds

from nti.zope_catalog.catalog import Catalog

from zope.mimetype.interfaces import IContentTypeAware

from nti.zope_catalog.topic import TopicIndex
from nti.zope_catalog.topic import ExtentFilteredSet

from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import SetIndex as RawSetIndex

from nti.zope_catalog.string import StringTokenNormalizer
from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.interfaces import IMetadataCatalog

class MimeTypeIndex(ValueIndex):
	default_field_name = 'mimeType'
	default_interface = IContentTypeAware

from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import TYPE_UUID
from nti.ntiids.ntiids import TYPE_INTID
from nti.ntiids.ntiids import TYPE_NAMED_ENTITY
from nti.ntiids.ntiids import TYPE_MEETINGROOM
from nti.ntiids.ntiids import is_ntiid_of_types
from nti.ntiids.ntiids import find_object_with_ntiid

class ValidatingContainerId(object):
	"""
	The "interface" we adapt to to find the container id.

	Rejects certain types of contained IDs from being indexed
	by returning a None value:

	* OID container IDs. These are seen on MessageInfo objects,
	  and, as they are always unique, are not helpful to index.
	  Likewise for UUID and INTIDs, although in practice these
	  are not yet used.

	  We make an exception for forum comments, which we do index
	  even if they have an excluded type for a container id. This is
	  because some forums, notably those associated with classes,
	  may not have better NTIIDs (yet), and we need these in the index
	  for notabledata to work (see ``_only_included_comments_in_my_topics_ntiids``).
	"""

	__slots__ = (b'containerId',)

	_IGNORED_TYPES = {TYPE_OID,TYPE_UUID,TYPE_INTID}

	def __init__(self, obj, default):
		contained = INTIContained(obj, default)
		if contained is not None:
			cid = contained.containerId
			if is_ntiid_of_types( cid, self._IGNORED_TYPES ) and not ICommentPost.providedBy(obj):
				self.containerId = None
			else:
				self.containerId = unicode(cid)

	def __reduce__(self):
		raise TypeError()

class ContainerIdIndex(ValueIndex):
	default_field_name = 'containerId'
	default_interface = ValidatingContainerId
# Will we use that with a string token normalizer?

# How to index creators? username? and just really
# hope that when a user is deleted the right events
# fire to remove all the indexed objects?

class CreatorRawIndex(RawValueIndex):
	pass
# We will use that with a string token normalizer

def CreatorIndex(family=None):
	return NormalizationWrapper(field_name='creator_username',
								interface=ICreatedUsername,
								index=CreatorRawIndex(family=family),
								normalizer=StringTokenNormalizer())

class SharedWithRawIndex(RawSetIndex):
	pass

def SharedWithIndex(family=None):
	# SharedWith is a mixin property, currently,
	# the interface it is defined on is not really
	# the one we want, therefore we just ask for it from
	# anyone
	return NormalizationWrapper(field_name='sharedWith',
								normalizer=StringTokenNormalizer(),
								index=SharedWithRawIndex(family=family),
								is_collection=True )

class TaggedToRawIndex(RawSetIndex):
	pass

class TaggedTo(object):
	"""
	The \"interface\" we adapt to in order to
	find entities that are tagged to by the object.

	We take anything that is :class:`.IUserTaggedContent`` and look inside the
	'tags' sequence defined by it. If we find something that looks
	like an NTIID for a named entity, we look up the entity, and if
	it exists, we return its NTIID or username: If the entity is globally
	named, then the username is returned, otherwise, if the entity is only
	locally named, the NTIID is returned.

	"""

	__slots__ = (b'context',)

	# Tags are normally lower cased, but depending on when we get called
	# it's vaguely possible that we might see an upper-case value?
	_ENTITY_TYPES = {TYPE_NAMED_ENTITY, TYPE_NAMED_ENTITY.lower(),
					 TYPE_MEETINGROOM, TYPE_MEETINGROOM.lower()}

	def __init__( self, context, default ):
		self.context = IUserTaggedContent(context, None)

	@property
	def tagged_usernames(self):
		if self.context is None:
			return ()

		raw_tags = self.context.tags
		# Most things don't have tags
		if not raw_tags:
			return ()

		username_tags = set()
		for raw_tag in raw_tags:
			if is_ntiid_of_types( raw_tag, self._ENTITY_TYPES ):
				entity = find_object_with_ntiid( raw_tag )
				if entity is not None:
					# We actually have to be a bit careful here; we only want
					# to catch certain types of entity tags, those that are either
					# to an individual or those that participate in security relationships;
					# (e.g., it doesn't help to use a regular FriendsList since that is effectively
					# flattened).
					# Currently, this abstraction doesn't exactly exist so we
					# are very specific about it. See also :mod:`sharing`
					if IUser.providedBy(entity):
						username_tags.add( entity.username )
					elif IDynamicSharingTargetFriendsList.providedBy(entity):
						username_tags.add( entity.NTIID )
		return username_tags

def TaggedToIndex(family=None):
	"""
	Indexes the NTIIDs of entities mentioned in tags.
	"""

	return NormalizationWrapper(field_name='tagged_usernames',
								normalizer=StringTokenNormalizer(),
								index=TaggedToRawIndex(family=family),
								interface=TaggedTo,
								is_collection=True )

class CreatorOfInReplyToRawIndex(RawValueIndex):
	pass

class CreatorOfInReplyTo(object):
	"""
	The 'interface' we use to find the creator
	name an object is in reply-to.
	"""

	__slots__ = (b'context',)

	def __init__( self, context, default ):
		self.context = context

	@property
	def creator_name_replied_to(self):
		try:
			return ICreatedUsername(self.context.inReplyTo).creator_username
		except (TypeError,AttributeError):
			return None

	def __reduce__(self):
		raise TypeError()

def CreatorOfInReplyToIndex(family=None):
	"Indexes all the replies to a particular user"
	return NormalizationWrapper(field_name='creator_name_replied_to',
								normalizer=StringTokenNormalizer(),
								index=CreatorOfInReplyToRawIndex(family=family),
								interface=CreatorOfInReplyTo)

def isTopLevelContentObjectFilter(extent, docid, document):
	# TODO: This is messy
	# NOTE: This is referenced by persistent objects, must stay
	if getattr(document, '__is_toplevel_content__', False):
		return True

	if IModeledContent.providedBy(document):
		if IFriendsList.providedBy(document) or IDevice.providedBy(document):
			# These things are modeled content, for some reason
			return False
		# HeadlinePosts (which are IMutedInStream) are threadable,
		# but we don't consider them top-level. (At this writing,
		# we don't consider the containing Topic to be top-level
		# either, because it isn't IModeledContent.)
		if IHeadlinePost.providedBy(document):
			return False

		if IInspectableWeakThreadable.providedBy(document):
			return not document.isOrWasChildInThread()
		if IThreadable.providedBy(document):
			return document.inReplyTo is None
		return True
	# Only modeled content; anything else is not

class TopLevelContentExtentFilteredSet(ExtentFilteredSet):
	"""
	A filter for a topic index that collects top-level objects.
	"""
	def __init__(self, id, family=None):
		super(TopLevelContentExtentFilteredSet,self).__init__(
			id,
			isTopLevelContentObjectFilter,
			family=family)

def isDeletedObjectPlaceholder(extent, docid, document):
	# NOTE: This is referenced by persistent objects, must stay.
	return IDeletedObjectPlaceholder.providedBy(document)

class DeletedObjectPlaceholderExtentFilteredSet(ExtentFilteredSet):
	"""
	A filter for a topic index that collects deleted placeholders.
	"""
	def __init__(self, id, family=None):
		super(DeletedObjectPlaceholderExtentFilteredSet,self).__init__(
			id,
			isDeletedObjectPlaceholder,
			family=family)

class CreatedTimeRawIndex(RawIntegerValueIndex):
	pass

def CreatedTimeIndex(family=None):
	return NormalizationWrapper(field_name='createdTime',
								interface=ILastModified,
								index=CreatedTimeRawIndex(family=family),
								normalizer=TimestampToNormalized64BitIntNormalizer())

class LastModifiedRawIndex(RawIntegerValueIndex):
	pass

def LastModifiedIndex(family=None):
	return NormalizationWrapper(field_name='lastModified',
								interface=ILastModified,
								index=LastModifiedRawIndex(family=family),
								normalizer=TimestampToNormalized64BitIntNormalizer())

IX_MIMETYPE = 'mimeType'
IX_CONTAINERID = 'containerId'
IX_CREATOR = 'creator'
IX_CREATEDTIME = 'createdTime'
IX_LASTMODIFIED = 'lastModified'
IX_SHAREDWITH = 'sharedWith'
IX_REPLIES_TO_CREATOR = 'repliesToCreator'
IX_TAGGEDTO = 'taggedTo'
IX_TOPICS = 'topics'

#: The name of the topic/group in the topics index
#: that stores top-level content.
#: See :class:`TopLevelContentExtentFilteredSet`
TP_TOP_LEVEL_CONTENT = 'topLevelContent'

#: The name of the topic/group in the topics index
#: that stores deleted placeholders.
#: See :class:`DeletedObjectPlaceholderExtentFilteredSet`
TP_DELETED_PLACEHOLDER = 'deletedObjectPlaceholder'

@interface.implementer(IMetadataCatalog)
class MetadataCatalog(Catalog):

	super_index_doc = Catalog.index_doc

	def index_doc(self, id, ob):
		# We do not want to index here. We'll index via our catalog processor.
		pass

	def force_index_doc(self, id, ob):
		self.super_index_doc( id, ob )

def install_metadata_catalog( site_manager_container, intids=None ):
	"""
	Installs the global metadata catalog.
	"""

	lsm = site_manager_container.getSiteManager()
	if intids is None:
		intids = lsm.getUtility(IIntIds)

	catalog = MetadataCatalog(family=intids.family)
	catalog.__name__ = CATALOG_NAME
	catalog.__parent__ = site_manager_container
	intids.register( catalog )
	lsm.registerUtility( catalog, provided=ICatalog, name=CATALOG_NAME )

	for name, clazz in ( (IX_MIMETYPE, MimeTypeIndex),
						 (IX_CONTAINERID, ContainerIdIndex),
						 (IX_CREATOR, CreatorIndex),
						 (IX_CREATEDTIME, CreatedTimeIndex),
						 (IX_LASTMODIFIED, LastModifiedIndex),
						 (IX_SHAREDWITH, SharedWithIndex),
						 (IX_REPLIES_TO_CREATOR, CreatorOfInReplyToIndex),
						 (IX_TAGGEDTO, TaggedToIndex),
						 (IX_TOPICS, TopicIndex)):
		index = clazz( family=intids.family )
		assert ICatalogIndex.providedBy(index)
		intids.register( index )
		# As a very minor optimization for unit tests, if we
		# already set the name and parent of the index,
		# the ObjectAddedEvent won't be fired
		# when we add the index to the catalog.
		# ObjectAdded/Removed events *must* fire during evolution,
		# though.
		index.__name__ = name
		index.__parent__ = catalog
		catalog[name] = index

	topic_index = catalog['topics']
	for filter_id, factory in ( (TP_TOP_LEVEL_CONTENT, TopLevelContentExtentFilteredSet),
								(TP_DELETED_PLACEHOLDER, DeletedObjectPlaceholderExtentFilteredSet)):
		the_filter = factory(filter_id, family=intids.family)
		topic_index.addFilter(the_filter)


	return catalog

from .interfaces import IEntity
from zope.lifecycleevent import IObjectRemovedEvent

@component.adapter(IEntity, IObjectRemovedEvent)
def clear_replies_to_creator_when_creator_removed(entity, event):
	"""
	When a creator is removed, all of the things that were direct
	replies to that creator are now \"orphans\", with a value
	for ``inReplyTo``. We clear out the index entry for ``repliesToCreator``
	for this entity in that case.

	The same scenario holds for things that were shared directly
	to that user.
	"""

	catalog = component.queryUtility(ICatalog, name=CATALOG_NAME)
	if catalog is None:
		# Not installed yet
		return

	# These we can simply remove, this creator doesn't exist anymore
	for ix_name in 'repliesToCreator', 'taggedTo':
		index = catalog[ix_name]
		query = {ix_name: {'any_of': (entity.username,)} }
		results = catalog.searchResults(**query)
		for uid in results.uids:
			index.unindex_doc(uid)

	# These, though, may still be shared, so we need to reindex them
	index = catalog['sharedWith']
	results = catalog.searchResults(sharedWith={'all_of': (entity.username,)})
	uidutil = results.uidutil
	for uid in results.uids:
		obj = uidutil.getObject(uid)
		index.index_doc(uid, obj)
