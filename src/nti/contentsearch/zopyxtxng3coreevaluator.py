# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
import collections

from zopyx.txng3.core import evaluator as zopyx_evaluator
from zopyx.txng3.core import parsetree as zopyx_parsetree

from nti.contentsearch.zopyxtxng3coreresultset import intersectionResultSets

class Evaluator(zopyx_evaluator.Evaluator):
	
	def PhraseNode(self, node):
		# Dealing with PhraseNodes is somewhat tricks
		# node.getValue() should return a sequence of WordNodes representing
		# the terms of the phrase
		
		# first tcreate he a copy of the ordered(!) terms
		words = [n.getValue() for n in node.getValue()]
	
		idx = 0
		while idx < len(words):
			seq = words[idx]
			if isinstance(seq, collections.Iterable) and not isinstance(seq, six.string_types) :
				words.pop(idx)
				words.extend(seq)
			elif isinstance(seq, zopyx_parsetree.BaseNode):
				words[idx] = seq.getValue()
			else:
				idx += 1
		
		# So first perform a simple word search for all terms
		sets = [self(n) for n in node.getValue()]
		
		# Now intersect the results (AND). This descreases the number of documents
		# to be checked.
		rs = intersectionResultSets(sets) 
		
		# Now check if the found documents really contain the words as phrase
		return zopyx_evaluator.lookup_by_phrase(self.searchrequest, 
		                        				rs.getDocids(), 
		                        		  		words,
		                        		    	self._getField(node))
				