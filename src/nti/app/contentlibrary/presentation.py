#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.intid.interfaces import IntIdAddedEvent

from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contenttypes.presentation.interfaces import INTICourseOverviewGroup
from nti.contenttypes.presentation.interfaces import IPackagePresentationAsset

@component.adapter(INTICourseOverviewGroup, IntIdAddedEvent)
def _on_course_overview_registered(group, event):
	catalog = get_library_catalog()
	for item in group:
		if IPackagePresentationAsset.providedBy(item):
			catalog.update_containers(item, group.ntiid)
