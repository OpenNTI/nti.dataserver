#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Based on Zope2.OFS.Item

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent

from Acquisition import Implicit

from ExtensionClass import Base

from zope.interface import implementer

from persistent import Persistent

from nti.common.property import alias

from .interfaces import IItem
from .interfaces import ISimpleItem
from .interfaces import IItemWithName

from .traversable import Traversable

@implementer(IItem)
class Item(Base, Traversable):
	"""
	A common base class for simple, non-container objects.
	"""

	id = ''

	def getId(self):
		"""
		Return the id of the object as a string.

		This method should be used in preference to accessing an id attribute
		of an object directly. The getId method is public.
		"""
		name = getattr(self, 'id', None)
		if callable(name):
			return name()
		if name is not None:
			return name
		if hasattr(self, '__name__'):
			return self.__name__
		raise AttributeError, 'This object has no id'

	__name__ = alias('id')

	# Name, relative to BASEPATH1 of icon used to display item
	# in folder listings.
	icon = ''

	# Default title.
	title = ''

	def title_or_id(self):
		"""
		Return the title if it is not blank and the id otherwise.
		"""
		title = self.title
		if callable(title):
			title = title()
		if title: return title
		return self.getId()

	def title_and_id(self):
		"""
		Return the title if it is not blank and the id otherwise.

		If the title is not blank, then the id is included in parens.
		"""
		title = self.title
		if callable(title):
			title = title()
		uid = self.getId()
		return title and ("%s (%s)" % (title, uid)) or uid

	def this(self):
		# Handy way to talk to ourselves in document templates.
		return self

	# This keeps simple items from acquiring their parents
	# objectValues, etc., when used in simple tree tags.
	def objectValues(self, spec=None):
		return ()
	objectIds = objectItems = objectValues

	def __len__(self):
		return 1

	def __repr__(self):
		"""
		Show the physical path of the object and its context if available.
		"""
		try:
			path = '/'.join(self.getPhysicalPath())
		except:
			return Base.__repr__(self)
		context_path = None
		context = aq_parent(self)
		container = aq_parent(aq_inner(self))
		if aq_base(context) is not aq_base(container):
			try:
				context_path = '/'.join(context.getPhysicalPath())
			except:
				context_path = None
		res = '<%s' % self.__class__.__name__
		res += ' at %s' % path
		if context_path:
			res += ' used for %s' % context_path
		res += '>'
		return res

@implementer(IItemWithName)
class ItemWithName(Item):
	"""
	Mixin class to support common name/id functions"""

	def getId(self):
		"""
		Return the id of the object as a string.
		"""
		return self.__name__

	def title_or_id(self):
		"""
		Return the title if it is not blank and the id otherwise.
		"""
		return self.title or self.__name__

	def title_and_id(self):
		"""
		Return the title if it is not blank and the id otherwise.

		If the title is not blank, then the id is included in parens.
		"""
		t = self.title
		return t and ("%s (%s)" % (t, self.__name__)) or self.__name__

	def _setId(self, uid):
		self.__name__ = uid

	def getPhysicalPath(self):
		"""
		Get the physical path of the object.

		Returns a path (an immutable sequence of strings) that can be used to
		access this object again later, for example in a copy/paste operation.
		getPhysicalRoot() and getPhysicalPath() are designed to operate
		together.
		"""
		path = (self.__name__,)

		p = aq_parent(aq_inner(self))
		if p is not None:
			path = p.getPhysicalPath() + path

		return path

@implementer(ISimpleItem)
class SimpleItem(Item,
				 Persistent,
				 Implicit):
	"""
	Mix-in class combining the most common set of basic mix-ins
	"""
