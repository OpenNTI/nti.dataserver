#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search fragments

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import namedtuple

from zope import interface

from zope.interface.common.sequence import IFiniteSequence

from nti.externalization.representation import WithRepr

from nti.schema.eqhash import EqHash

from .interfaces import ISearchFragment

Range = namedtuple('Range', ('start', 'end'))

def is_word_start(idx, text, punkt_pattern):
	result = idx == 0 or punkt_pattern.match(text[idx - 1])
	return result

def is_word_end(idx, text, punkt_pattern):
	result = idx == len(text) or punkt_pattern.match(text[idx])
	return result

def is_range_subsumed(refidx, v, ranges):
	for idx, t in enumerate(ranges):
		if idx != refidx:
			if v.start >= t.start and v.end <= t.end:
				return True
	return False

def clean_ranges(matches):
	result = []
	for idx, r in enumerate(matches):
		if not is_range_subsumed(idx, r, matches):
			result.append(r)
	return result

def match_terms(fragment, termset, check_start_word, check_end_word, punkt_pattern):
	matches = []
	for term in termset:
		idx = 0
		_len = len(term)
		idx = fragment.find(term, idx)
		while idx >= 0:
			endidx = idx + _len
			if  (not check_start_word or
					 is_word_start(idx, fragment, punkt_pattern)) and \
				(not check_end_word or
					 is_word_end(endidx, fragment, punkt_pattern)):
				mrange = Range(idx, endidx)
				matches.append(mrange)
			idx = fragment.find(term, endidx)
	matches = clean_ranges(matches)
	return matches

def create_from_whoosh_fragment(whoosh_fragment, termset, punkt_pattern):
	matches = []
	termset = set(termset)
	offset = whoosh_fragment.startchar
	for t in whoosh_fragment.matches:
		txt = t.text.lower()
		if txt in termset:
			termset.remove(txt)
		idx = t.startchar - offset
		endidx = t.endchar - offset
		mrange = Range(idx, endidx)
		matches.append(mrange)

	fragment = whoosh_fragment.text[whoosh_fragment.startchar:whoosh_fragment.endchar]
	if termset:
		m = match_terms(fragment.lower(), termset, True, False, punkt_pattern)
		matches.extend(m)
		matches = sorted(matches, key=lambda ra: ra.start)

	result = SearchFragment()
	result.text = fragment
	result.matches = matches if matches else ()
	return result

def create_from_terms(text, termset, check_word, punkt_pattern):
	fragment = text
	matches = match_terms(fragment.lower(), termset, check_word, check_word,
						  punkt_pattern)
	matches = sorted(matches, key=lambda ra: ra.start)
	result = SearchFragment()
	result.text = fragment
	result.matches = matches if matches else ()
	return result

@WithRepr
@EqHash('text', 'matches')
@interface.implementer(ISearchFragment, IFiniteSequence)
class SearchFragment(object):

	mime_type = mimeType = 'application/vnd.nextthought.search.searchfragment'

	field = None

	def __len__(self):
		return len(self.matches)

	def __iter__(self):
		return iter(self.matches)
