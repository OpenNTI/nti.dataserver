#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Based on Zope2.OFS.Folder and Zope2.OFS.ObjectManager

.. $id: __init__.py 59494 2015-02-14 02:16:29Z carlos.sanchez $
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from .interfaces import IFolder

from .item import Item

from .objectmanager import ObjectManager

@interface.implementer(IFolder)
class Folder(ObjectManager, Item):

	def __init__(self, uid=None):
		if uid is not None:
			self.id = str(uid)

class Root(Folder):
	"""
	Top-level object
	"""

	title = 'Root'
	
	def id(self):
		return self.title

	def title_and_id(self):
		return self.title

	def title_or_id(self):
		return self.title

	def absolute_url(self, relative=0):
		"""
		The absolute URL of the root object is BASE1 or "/".
		"""
		if relative: 
			return ''
		return '/'

	def absolute_url_path(self):
		"""
		The absolute URL path of the root object is BASEPATH1 or "/".
		"""
		return '/'

	def virtual_url_path(self):
		"""
		The virtual URL path of the root object is empty.
		"""
		return ''

	def getPhysicalRoot(self):
		return self

	def getPhysicalPath(self):
		"""
		Get the physical path of the object.

		Returns a path (an immutable sequence of strings) that can be used to
		access this object again later, for example in a copy/paste operation.
		getPhysicalRoot() and getPhysicalPath() are designed to operate
		together.
		"""
		# We're at the base of the path.
		return ('',)
