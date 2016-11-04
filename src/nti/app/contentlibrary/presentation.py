#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from nti.intid.interfaces import IntIdAddedEvent

from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contenttypes.presentation.interfaces import INTICourseOverviewGroup
from nti.contenttypes.presentation.interfaces import IPackagePresentationAsset

@component.adapter(INTICourseOverviewGroup, IntIdAddedEvent)
def _on_course_overview_registered(group, event):
	parent = group.__parent__
	catalog = get_library_catalog()
	extended = (group.ntiid, getattr(parent, 'ntiid', None))
	for item in group:
		if IPackagePresentationAsset.providedBy(item):
			catalog.update_containers(item, extended)

@component.adapter(INTICourseOverviewGroup, IObjectModifiedEvent)
def _on_course_overview_modified(group, event):
	_on_course_overview_registered(group, None)
