#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.lifecycleevent.interfaces import IObjectMovedEvent

from nti.base.interfaces import IFile

from nti.contentfolder.interfaces import IContentFolder


@component.adapter(IFile, IObjectMovedEvent)
def _on_content_file_moved(unused_context, event):
    if IContentFolder.providedBy(event.newParent):
        try:
            event.newParent.updateLastMod()
        except AttributeError:
            pass
