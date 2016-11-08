#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.lifecycleevent.interfaces import IObjectAddedEvent

from nti.app.contentfile.view_mixins import validate_sources

from nti.app.authentication import get_remote_user

from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfolder.interfaces import IContentFolder

@component.adapter(IContentBaseFile, IObjectAddedEvent)
def _on_content_file_added(context, event):
	if IContentFolder.providedBy(event.newParent):
		user = get_remote_user()
		validate_sources(user, event.newParent, sources=(context,))
