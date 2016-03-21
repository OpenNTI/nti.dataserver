#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from BTrees.OOBTree import OOTreeSet

from nti.common.property import alias

from nti.common import sets

from nti.contentfile.interfaces import IContentFile
from nti.contentfile.interfaces import IContentImage
from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage

from nti.namedfile.file import NamedFile
from nti.namedfile.file import NamedImage
from nti.namedfile.file import NamedBlobFile
from nti.namedfile.file import NamedBlobImage

from nti.wref.interfaces import IWeakRef

class BaseContentMixin(object):

	creator = None
	__name__ = alias('name')

	def _lazy_create_ootreeset_for_wref(self):
		self._p_changed = True
		result = OOTreeSet()
		if self._p_jar:
			self._p_jar.add(result)
		return result

	def _remove_entity_from_named_lazy_set_of_wrefs(self, name, context):
		self._p_activate()
		if name in self.__dict__:
			jar = getattr(self, '_p_jar', None)
			container = getattr(self, name)
			if jar is not None:
				jar.readCurrent(self)
				container._p_activate()
				jar.readCurrent(container)
			wref = IWeakRef(context, None)
			if wref is not None:
				__traceback_info__ = context, wref
				sets.discard(container, wref)

BaseMixin = BaseContentMixin  # BWC

@interface.implementer(IContentFile)
class ContentFile(NamedFile, BaseContentMixin):
	pass

@interface.implementer(IContentBlobFile)
class ContentBlobFile(NamedBlobFile, BaseContentMixin):
	pass

@interface.implementer(IContentImage)
class ContentImage(NamedImage, BaseContentMixin):
	pass

@interface.implementer(IContentBlobImage)
class ContentBlobImage(NamedBlobImage, BaseContentMixin):
	pass
