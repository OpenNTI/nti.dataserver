#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.contentfolder.interfaces import IContentFolder

from nti.externalization.interfaces import IExternalObjectDecorator

from nti.externalization.singleton import SingletonDecorator

@component.adapter(IContentFolder)
@interface.implementer(IExternalObjectDecorator)
class ContentFolderDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		# XXX: Remove IContentTypeAware fields
		external.pop('parameters', None)
		external.pop('mimeType', None)
