#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.lifecycleevent.interfaces import IObjectMovedEvent

from nti.base.interfaces import IFile

from nti.contentfolder.interfaces import IContentFolder

logger = __import__('logging').getLogger(__name__)


@component.adapter(IFile, IObjectMovedEvent)
def _on_content_file_moved(unused_context, event):
    if IContentFolder.providedBy(event.newParent):
        try:
            event.newParent.updateLastMod()
        except AttributeError:  # pragma: no cover
            pass
