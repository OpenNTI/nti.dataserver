#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of content bundles.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.utils.property import alias

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createFieldProperties

from persistent import Persistent

# Because we only expect to store persistent versions
# of these things, and we expect to update them directly
# in place, we make them attribute annotatable.
from zope.annotation.interfaces import IAttributeAnnotatable

from .interfaces import IContentPackageBundle
from .interfaces import IContentPackageBundleLibrary

from nti.wref.interfaces import IWeakRef

from nti.dataserver.containers import CheckingLastModifiedBTreeContainer

@interface.implementer(IContentPackageBundle,
					   IAttributeAnnotatable)
class ContentPackageBundle(SchemaConfigured):
	"""
	Basic implementation of a content package bundle.
	"""
	__external_class_name__ = 'ContentPackageBundle'
	__external_can_create__ = False

	createFieldProperties(IContentPackageBundle)

	# the above defined the ntiid property and the name
	# property, but the ntiid property has the constraint on it
	# that we need.
	__name__ = alias('ntiid')

class PersistentContentPackageBundle(SchemaConfigured,
									 Persistent):
	"""
	A persistent implementation of content package bundles.

	As required, references to content packages are
	maintained weakly.
	"""

	_ContentPackages_wrefs = ()

	def _set_ContentPackages(self, packages):
		self._ContentPackages_wrefs = tuple([IWeakRef(p) for p in packages])
		if len(self._ContentPackages_wrefs) != len(set(self._ContentPackages_wrefs)):
			raise ValueError("Duplicate packages")
	def _get_ContentPackages(self):
		for x in self._ContentPackages_wrefs:
			x = x()
			if x is not None:
				yield x
	ContentPackages = property(_get_ContentPackages, _set_ContentPackages)


@interface.implementer(IContentPackageBundleLibrary)
class ContentPackageBundleLibrary(CheckingLastModifiedBTreeContainer):
	"""
	BTree-based implementation of a bundle library.
	"""
	__external_can_create__ = False

	# TODO: APIs for walking up the utility tree
