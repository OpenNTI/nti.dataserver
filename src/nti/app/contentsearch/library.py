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

from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentsearch.interfaces import IRootPackageResolver
from nti.contentsearch.interfaces import ISearchPackageResolver

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import is_ntiid_of_type
from nti.ntiids.ntiids import find_object_with_ntiid

@interface.implementer(ISearchPackageResolver)
class _DefaultSearchPacakgeResolver(object):

	def __init__(self, *args):
		pass

	def resolve(self, user, ntiid=None):
		result = set()
		if ntiid != ROOT:
			if bool(is_ntiid_of_type(ntiid, TYPE_OID)):
				obj = find_object_with_ntiid(ntiid)
				bundle = IContentPackageBundle(obj, None)
				if bundle is not None and bundle.ContentPackages:
					result = tuple(x.ntiid for x in bundle.ContentPackages)
			else:
				result = (ntiid,)
		return result

@interface.implementer(IRootPackageResolver)
class _DefaultRootPackageResolver(object):

	def __init__(self, *args):
		pass

	def get_ntiid_path(self, ntiid):
		library = component.queryUtility(IContentPackageLibrary)
		if library and ntiid:
			paths = library.pathToNTIID(ntiid)
			return tuple(p.ntiid for p in paths) if paths else ()
		return ()

	def resolve(self, ntiid):
		library = component.queryUtility(IContentPackageLibrary)
		paths = library.pathToNTIID(ntiid) if library else None
		return paths[0] if paths else None
