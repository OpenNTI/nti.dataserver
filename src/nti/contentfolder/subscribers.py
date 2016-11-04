#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.lifecycleevent.interfaces import IObjectMovedEvent

from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfolder.interfaces import IContentFolder

@component.adapter(IContentBaseFile, IObjectMovedEvent)
def _on_content_file_moved(context, event):
	if IContentFolder.providedBy(event.newParent):
		try:
			event.newParent.updateLastMod()
		except AttributeError:
			pass
