#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for forums.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface
from zope import component

import Acquisition
from persistent import Persistent

from nti.dataserver import containers
from nti.dataserver import sharing

from nti.utils.schema import AdaptingFieldProperty
#from zope.schema.fieldproperty import FieldProperty

from . import interfaces as for_interfaces
from zope.annotation import interfaces as an_interfaces

@interface.implementer(for_interfaces.IForum, an_interfaces.IAttributeAnnotatable)
class Forum(Acquisition.Implicit,
			containers.AcquireObjectsOnReadMixin,
			containers.CheckingLastModifiedBTreeContainer,
			sharing.AbstractReadableSharedWithMixin):

	__external_can_create__ = False
	title = AdaptingFieldProperty(for_interfaces.IForum['title'])
	description = AdaptingFieldProperty(for_interfaces.IBoard['description'])
	sharingTargets = ()
	TopicCount = property(containers.CheckingLastModifiedBTreeContainer.__len__)

@interface.implementer(for_interfaces.IPersonalBlog)
class PersonalBlog(Forum):
	__external_can_create__ = False
