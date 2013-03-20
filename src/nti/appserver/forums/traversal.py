#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Related to traversing into forum objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.appserver._adapters import GenericModeledContentExternalFieldTraverser

@component.adapter(frm_interfaces.IPost)
class _PostFieldTraverser(GenericModeledContentExternalFieldTraverser):
	"Disallow updates to the sharedWith field of blog posts/comments"
	_allowed_fields = tuple( set(GenericModeledContentExternalFieldTraverser._allowed_fields) - set( ('sharedWith',)) )
