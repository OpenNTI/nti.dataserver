#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization for forum objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver.interfaces import IThreadable

from ..threadable import ThreadableExternalizableMixin
from ..base import UserContentRootInternalObjectIOMixin

class _MaybeThreadableForumObjectInternalObjectIO(ThreadableExternalizableMixin,UserContentRootInternalObjectIOMixin):
	"""
	Some of our objects are threadable, some are not, so
	we distinguish here. This was easier than registering custom
	objects for the specific interfaces.

	.. note: We are not enforcing that replies are to objects in the same
		topic.
	"""

	def _ext_can_write_threads(self):
		return IThreadable.providedBy(self._ext_replacement() )

	def _ext_can_update_threads(self):
		return (super(_MaybeThreadableForumObjectInternalObjectIO,self)._ext_can_update_threads()
				and IThreadable.providedBy(self._ext_replacement()))
