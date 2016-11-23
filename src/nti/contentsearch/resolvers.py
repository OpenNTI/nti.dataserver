#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.contentlibrary.interfaces import IContentPackageBundle

from nti.contentsearch.interfaces import ISearchPackageResolver

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import is_ntiid_of_type
from nti.ntiids.ntiids import find_object_with_ntiid

@interface.implementer(ISearchPackageResolver)
class DefaultSearchPacakgeResolver(object):

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
