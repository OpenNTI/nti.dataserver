#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.container.contained import contained
from zope.container.interfaces import IContained

from ZODB.interfaces import IConnection

from nti.dataserver.interfaces import IModeledContent

from nti.schema.interfaces import IBeforeSequenceAssignedEvent

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.containers.containers",
    "nti.containers.containers",
    "_IdGenerationMixin",
    "IdGeneratorNameChooser",
    "ExhaustedUniqueIdsError",
    "AbstractNTIIDSafeNameChooser",
    "AcquireObjectsOnReadMixin",
    "_CheckObjectOnSetMixin",
    "ModDateTrackingBTreeContainer",
    "CheckingLastModifiedBTreeContainer",
    "CheckingLastModifiedBTreeFolder",
    "EventlessLastModifiedBTreeContainer",
    "_CaseInsensitiveKey",
    "LastModifiedBTreeContainer",
    "CaseInsensitiveLastModifiedBTreeContainer",
    "KeyPreservingCaseInsensitiveModDateTrackingBTreeContainer",
    "CaseInsensitiveLastModifiedBTreeFolder",
    "CaseInsensitiveCheckingLastModifiedBTreeFolder",
    "CaseInsensitiveCheckingLastModifiedBTreeContainer")

@component.adapter(None, IModeledContent, IBeforeSequenceAssignedEvent)
def contain_nested_objects(sequence, parent, event):
	"""
	New, incoming objects like a Canvas need to be added to the parent container
	when a sequence containing them is set. (e.g., the body of a Note)
	"""
	if sequence is None:
		return

	for i, child in enumerate(sequence):
		if IContained.providedBy(child):
			name = getattr(child, '__name__', None) or unicode(i)
			contained(child, parent, name)
			jar = IConnection(child, None)  # Use either its pre-existing jar, or the parents
			if jar and not getattr(child, '_p_oid', None):
				jar.add(child)
