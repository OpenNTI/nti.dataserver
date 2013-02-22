#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions of boards.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface
from zope import component

from zope.container.constraints import checkObject

import ExtensionClass
from persistent import Persistent

from nti.dataserver import datastructures
from nti.dataserver import containers
from nti.dataserver import sharing


from nti.utils.schema import AdaptingFieldProperty
from . import interfaces as for_interfaces

@interface.implementer(for_interfaces.IBoard)
class Board(ExtensionClass.Base,
			containers.AcquireObjectsOnReadMixin,
			containers.CheckingLastModifiedBTreeContainer,
			sharing.AbstractReadableSharedWithMixin):

	__external_can_create__ = False

	title = AdaptingFieldProperty(for_interfaces.IBoard['title'])
	description = AdaptingFieldProperty(for_interfaces.IBoard['description'])

	ForumCount = property(containers.CheckingLastModifiedBTreeContainer.__len__)

	sharingTargets = ()
