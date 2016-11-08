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

from zope.location.interfaces import IContained

from nti.contentfile.datastructures import ContentBlobFileObjectIO

from nti.contentfile.model import ContentBlobFile

from nti.dataserver.contenttypes.base import UserContentRoot

from nti.dataserver.contenttypes.threadable import ThreadableMixin

from nti.dataserver.interfaces import IModeledContentFile

@interface.implementer(IModeledContentFile, IContained)
class ModeledContentFile(ThreadableMixin,
				 		 UserContentRoot,
				  		 ContentBlobFile):

	parameters = None

	def __init__(self, *args, **kwargs):
		ThreadableMixin.__init__(self)
		UserContentRoot.__init__(self)
		ContentBlobFile.__init__(self, *args, **kwargs)
		self.parameters = {}

@component.adapter(IModeledContentFile)
class _ModeledContentFileObjectIO(ContentBlobFileObjectIO):

	_ext_iface_upper_bound = IModeledContentFile
	_excluded_in_ivars_ = {'download_url'}.union(ContentBlobFileObjectIO._excluded_in_ivars_)

	def _ext_mimeType(self, obj):
		return u'application/vnd.nextthought.modeledcontentfile'

def _ModeledContentFileFactory(ext_obj):
	factory = ModeledContentFile
	return factory
