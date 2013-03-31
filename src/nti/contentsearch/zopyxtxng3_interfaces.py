# -*- coding: utf-8 -*-
"""
TextIndexNG3 repoze catalog interfaces.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

from zope.index import interfaces as zidx_interfaces

from repoze.catalog import interfaces as rcat_interfaces

class ITextIndexNG3(zidx_interfaces.IInjection, zidx_interfaces.IIndexSearch, zidx_interfaces.IStatistics):

	def suggest(term, threshold, prefix):
		"""
		return a list of similar words based on the levenshtein distance
		"""

	def getLexicon():
		"""
		return the zopyx.txng3.core.interfaces.ILexicon for this text index
		"""

	def setLexicon(lexicon):
		"""
		set the zopyx.txng3.core.interfaces.ILexicon for this text index
		"""

class ICatalogTextIndexNG3(rcat_interfaces.ICatalogIndex, zidx_interfaces.IIndexSort, ITextIndexNG3):
	pass
