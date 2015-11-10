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

from nti.folder.objectmanager import ObjectManager

@interface.implementer(IFolder)
class Folder(ObjectManager, Item):

	def __init__(self, uid=None):
		if uid is not None:
			self.id = str(uid)
