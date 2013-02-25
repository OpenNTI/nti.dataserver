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
from Acquisition import aq_parent

from nti.dataserver import containers
from nti.dataserver import sharing

from zope.schema.fieldproperty import FieldProperty
from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import AcquisitionFieldProperty

from . import interfaces as for_interfaces
from zope.annotation import interfaces as an_interfaces

@interface.implementer(for_interfaces.ITopic, an_interfaces.IAttributeAnnotatable)
class Topic(Acquisition.Implicit,
			containers.AcquireObjectsOnReadMixin,
			containers.CheckingLastModifiedBTreeContainer,
			sharing.AbstractReadableSharedWithMixin):
	title = AdaptingFieldProperty(for_interfaces.ITopic['title'])
	description = AdaptingFieldProperty(for_interfaces.IBoard['description'])
	sharingTargets = ()
	tags = FieldProperty(for_interfaces.IPost['tags'])
	PostCount = property(containers.CheckingLastModifiedBTreeContainer.__len__)

@interface.implementer(for_interfaces.IHeadlineTopic)
class HeadlineTopic(Topic):
	headline = AcquisitionFieldProperty(for_interfaces.IHeadlineTopic['headline'])


# These one is never permissioned separately, only
# inherited. The inheritance is expressed through the ACLs, but
# in is convenient for the actual values to be accessible down here too.
# We have to do something special to override the default value set in the
# class we inherit from. cf post.PersonalBlog*
# TODO: Still not sure this is really correct
from . import _AcquiredSharingTargetsProperty
@interface.implementer(for_interfaces.IPersonalBlogEntry)
class PersonalBlogEntry(HeadlineTopic):
	creator = None
	headline = AcquisitionFieldProperty(for_interfaces.IPersonalBlogEntry['headline'])

	sharingTargets = _AcquiredSharingTargetsProperty()

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
