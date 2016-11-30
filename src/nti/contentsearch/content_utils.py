#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.common.string import to_unicode

from nti.contentsearch.interfaces import IRootPackageResolver

from nti.contentprocessing import tokenize_content
from nti.contentprocessing import get_content_translation_table

def get_collection_root(ntiid):
	resolver = component.queryUtility(IRootPackageResolver)
	return resolver.resolve(ntiid) if resolver is not None else None

def get_collection_root_ntiid(ntiid):
	croot = get_collection_root(ntiid)
	return croot.ntiid if croot else None

def get_content(text=None, language='en'):
	result = ()
	text = unicode(text) if text else None
	if text:
		table = get_content_translation_table(language)
		result = tokenize_content(text.translate(table), language)
	result = ' '.join(result)
	return to_unicode(result)
