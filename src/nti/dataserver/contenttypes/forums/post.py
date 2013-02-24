#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for forum posts.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

import Acquisition
from persistent import Persistent

from nti.dataserver import datastructures
from nti.dataserver import sharing
from nti.utils.schema import PermissiveSchemaConfigured

from ..note import BodyFieldProperty
from nti.utils.schema import AdaptingFieldProperty
from zope.schema.fieldproperty import FieldProperty

from . import interfaces as for_interfaces
from zope.annotation import interfaces as an_interfaces

@interface.implementer(for_interfaces.IPost, an_interfaces.IAttributeAnnotatable)
class Post(Acquisition.Implicit,
		   Persistent,
		   datastructures.ZContainedMixin,
		   datastructures.CreatedModDateTrackingObject,
		   sharing.AbstractReadableSharedWithMixin,
		   PermissiveSchemaConfigured ): # PSC must be last


	body = BodyFieldProperty(for_interfaces.IPost['body'])

	title = AdaptingFieldProperty(for_interfaces.IPost['title'])

	sharingTargets = ()

	def __eq__( self, other ):
		return other == (self.id, self.containerId, self.title, self.body, self.creator)
