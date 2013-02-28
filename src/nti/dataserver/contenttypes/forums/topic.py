#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for topics.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface

import Acquisition

from nti.ntiids import ntiids
from nti.dataserver import containers
from nti.dataserver import sharing

from zope.schema.fieldproperty import FieldProperty
from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import AcquisitionFieldProperty
from nti.utils.property import CachedProperty

from . import interfaces as for_interfaces
from zope.annotation import interfaces as an_interfaces

class _AbstractUnsharedTopic(containers.AcquireObjectsOnReadMixin,
							 containers.CheckingLastModifiedBTreeContainer,
							 Acquisition.Implicit):
	title = AdaptingFieldProperty(for_interfaces.ITopic['title'])
	description = AdaptingFieldProperty(for_interfaces.IBoard['description'])
	sharingTargets = ()
	tags = FieldProperty(for_interfaces.IPost['tags'])
	PostCount = property(containers.CheckingLastModifiedBTreeContainer.__len__)


@interface.implementer(for_interfaces.ITopic, an_interfaces.IAttributeAnnotatable)
class Topic(_AbstractUnsharedTopic,
			sharing.AbstractReadableSharedWithMixin):
	pass


@interface.implementer(for_interfaces.IHeadlineTopic)
class HeadlineTopic(Topic):
	headline = AcquisitionFieldProperty(for_interfaces.IHeadlineTopic['headline'])


# These one is permissioned by publication.

@interface.implementer(for_interfaces.IPersonalBlogEntry)
class PersonalBlogEntry(sharing.AbstractDefaultPublishableSharedWithMixin,
						HeadlineTopic):
	creator = None
	headline = AcquisitionFieldProperty(for_interfaces.IPersonalBlogEntry['headline'])

	@CachedProperty
	def NTIID(self):
		"NTIID is defined only after the creator and id/__name__ are set"
		return ntiids.make_ntiid( date=ntiids.DATE,
								  provider=self.creator.username,
								  nttype=for_interfaces.NTIID_TYPE_PERSONAL_BLOG_ENTRY,
								  specific=self.__name__ ) # will need to escape that

from zope.container.contained import ContainerSublocations
class HeadlineTopicSublocations(ContainerSublocations):
	"""
	Story topics contain their children and also their story.
	"""

	def sublocations( self ):
		for x in super(HeadlineTopicSublocations,self).sublocations():
			yield x
		story = self.container.headline
		if story is not None:
			yield story
