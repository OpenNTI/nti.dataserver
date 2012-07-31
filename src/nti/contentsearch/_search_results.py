from __future__ import print_function, unicode_literals

from nti.contentsearch.common import QUERY, HIT_COUNT, ITEMS, LAST_MODIFIED, SUGGESTIONS

import logging
logger = logging.getLogger( __name__ )

def _empty_result(query, is_suggest=False):
	result = {}
	result[QUERY] = query
	result[HIT_COUNT] = 0
	result[ITEMS] = [] if is_suggest else {}
	result[LAST_MODIFIED] = 0
	return result

def empty_search_result(query):
	return _empty_result(query)

def empty_suggest_and_search_result(query):
	result = _empty_result(query)
	result[SUGGESTIONS] = []
	return result

def empty_suggest_result(word):
	return _empty_result(word, True)

def merge_search_results(a, b):

	if not a and not b:
		return None
	elif not a and b:
		return b
	elif a and not b:
		return a

	alm = a.get(LAST_MODIFIED, 0)
	blm = b.get(LAST_MODIFIED, 0)
	a[LAST_MODIFIED] = max(alm, blm)

	if not a.has_key(ITEMS):
		a[ITEMS] = {}
	
	a[ITEMS].update(b.get(ITEMS, {}))
	a[HIT_COUNT] = len(a[ITEMS])
	return a

def merge_suggest_and_search_results(a, b):
	result = merge_search_results(a, b)
	s_a = set(a.get(SUGGESTIONS, [])) if a else set([])
	s_b = set(b.get(SUGGESTIONS, [])) if b else set([])
	s_a.update(s_b)
	result[SUGGESTIONS] = list(s_a)
	return result

def merge_suggest_results(a, b):

	if not a and not b:
		return None
	elif not a and b:
		return b
	elif a and not b:
		return a

	alm = a.get(LAST_MODIFIED, 0)
	blm = b.get(LAST_MODIFIED, 0)
	a[LAST_MODIFIED] = max(alm, blm)

	if not a.has_key(ITEMS):
		a[ITEMS] = []
	
	a_set = set(a.get(ITEMS,[]))
	a_set.update(b.get(ITEMS,[]))
	a[ITEMS] = list(a_set)
	a[HIT_COUNT] = len(a[ITEMS])
	return a

