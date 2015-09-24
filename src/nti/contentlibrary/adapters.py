#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adopter implementations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from .interfaces import IContentPackageLibrary
from .interfaces import IDelimitedHierarchyContentPackageEnumeration

@interface.implementer(IDelimitedHierarchyContentPackageEnumeration)
@component.adapter(IContentPackageLibrary)
def enumeration_from_library(library):
	"""
	Provide the library's enumeration.

	.. warning:: This relies on an implementation detail, the fact
		that all libraries we currently have use a library
		with this interface. This may break in the future,
		in which case this adapter will raise an exception.
	"""

	e = library._enumeration # pylint: disable=I0011,W0212
	assert IDelimitedHierarchyContentPackageEnumeration.providedBy(e)
	return e
