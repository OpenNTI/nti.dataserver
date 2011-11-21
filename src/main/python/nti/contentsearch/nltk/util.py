# Natural Language Toolkit: Simple Tokenizers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

import re
from re import finditer

def convert_regexp_to_nongrouping(pattern):
	"""
	Convert all grouping parenthases in the given regexp pattern to
	non-grouping parenthases, and return the result.  E.g.:
	
	    >>> convert_regexp_to_nongrouping('ab(c(x+)(z*))?d')
	    'ab(?:c(?:x+)(?:z*))?d'
	
	@type pattern: C{str}
	@rtype: C{str}
	"""
	# Sanity check: back-references are not allowed!
	for s in re.findall(r'\\.|\(\?P=', pattern):
		if s[1] in '0123456789' or s == '(?P=':
			raise ValueError('Regular expressions with back-references are not supported: %r' % pattern)

	# This regexp substitution function replaces the string '('
	# with the string '(?:', but otherwise makes no changes.
	def subfunc(m):
		return re.sub('^\((\?P<[^>]*>)?$', '(?:', m.group())

	# Scan through the regular expression.  If we see any backslashed
	# characters, ignore them.  If we see a named group, then
	# replace it with "(?:".  If we see any open parens that are part
	# of an extension group, ignore those too.  But if we see
	# any other open paren, replace it with "(?:")
	return re.sub(r'''(?x)
		\\.           |  # Backslashed character
		\(\?P<[^>]*>  |  # Named group
		\(\?          |  # Extension group
		\(               # Grouping parenthasis''', subfunc, pattern)

def string_span_tokenize(s, sep):
	"""
	Identify the tokens in the string, as defined by the token
	delimiter, and generate (start, end) offsets.
	
	@param s: the string to be tokenized
	@type s: C{str}
	@param sep: the token separator
	@type sep: C{str}
	@rtype: C{iter} of C{tuple} of C{int}
	"""
	if len(sep) == 0:
		raise ValueError, "Token delimiter must not be empty"
	left = 0
	while True:
		try:
			right = s.index(sep, left)
			if right != 0:
				yield left, right
		except ValueError:
			if left != len(s):
				yield left, len(s)
			break

		left = right + len(sep)

def regexp_span_tokenize(s, regexp):
	"""
	Identify the tokens in the string, as defined by the token
	delimiter regexp, and generate (start, end) offsets.
	
	@param s: the string to be tokenized
	@type s: C{str}
	@param regexp: the token separator regexp
	@type regexp: C{str}
	@rtype: C{iter} of C{tuple} of C{int}
	"""
	left = 0
	for m in finditer(regexp, s):
		right, next_ = m.span()
		if right != 0:
			yield left, right
		left = next_
	yield left, len(s)

def spans_to_relative(spans):
	"""
	Convert absolute token spans to relative spans.
	
	@param spans: the (start, end) offsets of the tokens
	@type s: C{iter} of C{tuple} of C{int}
	@rtype: C{iter} of C{tuple} of C{int}
	"""
	prev = 0
	for left, right in spans:
		yield left - prev, right - left
		prev = right

