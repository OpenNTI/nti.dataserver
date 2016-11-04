#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentprocessing.interfaces import INgramComputer

from nti.contentprocessing import tokenize_content
from nti.contentprocessing import get_content_translation_table

def get_library(library=None):
	if library is None:
		return component.queryUtility(IContentPackageLibrary)
	return library

def get_ntiid_path(ntiid, library=None):
	result = ()
	library = get_library(library)
	if library and ntiid:
		paths = library.pathToNTIID(ntiid)
		result = tuple(p.ntiid for p in paths) if paths else ()
	return result

def get_collection_root(ntiid, library=None):
	library = get_library(library)
	paths = library.pathToNTIID(ntiid) if library else None
	return paths[0] if paths else None

def get_collection_root_ntiid(ntiid, library=None):
	croot = get_collection_root(ntiid, library)
	result = croot.ntiid if croot else None
	return result

def get_content(text=None, language='en'):
	result = ()
	text = unicode(text) if text else None
	if text:
		table = get_content_translation_table(language)
		result = tokenize_content(text.translate(table), language)
	result = ' '.join(result)
	return unicode(result)

def is_covered_by_ngram_computer(term, language='en'):
	tokens = tokenize_content(term)
	__traceback_info__ = term, tokens
	ncomp = component.getUtility(INgramComputer, name=language)
	min_word = min(map(len, tokens)) if tokens else 0
	return min_word >= ncomp.minsize

