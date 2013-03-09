# -*- coding: utf-8 -*-
"""
Cosine ranking implementation.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from math import log, sqrt

from zope import interface

from zopyx.txng3.core.nbest import NBest
from zopyx.txng3.core.interfaces import IRanking
from zopyx.txng3.core.config import DEFAULT_LANGUAGE

@interface.implementer(IRanking)
def cosine_ranking(index, resultset, language=DEFAULT_LANGUAGE, maxhits=50):

	N = len(index)										# collection size, number of indexed documents
	nbest = NBest(maxhits)								# storage for the 'max' best hits
	word_field_sequence = resultset.getWords()			# sequence of (word, field) tuples
	lexicon_getWordId = index.getLexicon().getWordId	# shortcut

	IDF = {}											# inverse document frequency
	wid_cache = {}										# maps word -> wid for performance reasons
	storage_cache = {}									# cache for field -> index.getStorage(field)
	frequencies_cache = {}								# cache for field -> index.getStorage().getTermFrequency()

	# first calculate the inverse document frequency for all found words
	for word, field in word_field_sequence:

		# might be replaced with getWordIds()
		wid = lexicon_getWordId(word, language)
		if not wid: continue

		wid_cache[word] = wid
		if not storage_cache.has_key(field):
			storage_cache[field] = index.getStorage(field)
			frequencies_cache[field] = storage_cache[field].getTermFrequency()
		docids = storage_cache[field].getDocumentsForWordId(wid)
		TF = len(docids)   # term frequency

		# calculate the inverse document frequency
		if TF == 0:
			IDF[word] = 0
		else:
			IDF[word] = log(N / (TF+1.0)) + 1.0


	# now rank all documents
	for docid in resultset.getDocids():

		# accumulated rank
		rank = 0.0

		for word, field in word_field_sequence:
			wid = wid_cache.get(word)
			if not wid: continue

			# document term frequency
			try:
				DTF = frequencies_cache[field][docid][wid]
			except KeyError:
				DTF = 0

			# document term weight
			if DTF == 0:
				DTW = 0.0
			else:
				DTW = ((1.0 + log(DTF)) * IDF[word])

			# query term frequency and query max frequency are set to 1
			QTF = QMF = 1.0

			# query term weight
			QTW = ((0.5 + (0.5 * QTF / QMF))) * IDF[word]

			# accumulate rank
			rank += (DTW * QTW)

		# document weight
		DWT = sqrt(rank)

		# normalize rank
		if rank != 0.0:
			rank = rank / DWT

		# add to NBest instance - we are only interesed in the
		# documents with the best score (rank)
		nbest.add(docid, rank)

	return nbest.getbest()
