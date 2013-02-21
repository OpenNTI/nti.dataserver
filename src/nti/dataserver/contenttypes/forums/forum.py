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

from nti.dataserver import datastructures
from nti.dataserver import containers
from nti.dataserver import sharing
from nti.utils.schema import PermissiveSchemaConfigured

from ..note import BodyFieldProperty
from zope.schema.fieldproperty import FieldProperty

from . import interfaces as for_interfaces

@interface.implementer(for_interfaces.IForum)
class Forum(Acquisition.Implicit,
			containers.AcquireObjectsOnReadMixin,
			containers.CheckingLastModifiedBTreeContainer):
	title = FieldProperty(for_interfaces.IForum['title'])
