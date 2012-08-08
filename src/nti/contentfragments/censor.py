#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of the content censoring algorithms.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pkg_resources import resource_filename

from zope import interface

from nti.contentfragments import interfaces

# The algorithms contained in here are trivially simple.
# We could do much better, for example, with prefix trees.
# See https://hkn.eecs.berkeley.edu/~dyoo/python/ahocorasick/
# and http://pypi.python.org/pypi/trie/0.1.1

# If efficiency really matters, and we have many different filters we are
# applying, we would need to do a better job pipelining to avoid copies

@interface.implementer(interfaces.ICensoredContentStrategy)
class SimpleReplacementCensoredContentStrategy(object):

	def __init__( self, replacement_char='*' ):
		self.replacement_char = replacement_char
		assert len(self.replacement_char) == 1

	def censor( self, content_fragment, censored_ranges ):
		# Since we will be replacing each range with its equal length
		# of content and not shortening, then sorting the ranges doesn't matter
		buf = list(content_fragment)

		for start, end in censored_ranges:
			buf[start:end] = self.replacement_char * (end - start)

		new_fragment = ''.join( buf )
		try:
			return content_fragment.censored( new_fragment )
		except AttributeError:
			result = interfaces.CensoredUnicodeContentFragment( new_fragment )
			interface.alsoProvides( result, interfaces.ICensoredUnicodeContentFragment )
			return result

@interface.implementer(interfaces.ICensoredContentScanner)
class TrivialMatchScanner(object):

	def __init__( self, prohibited_values=() ):
		# normalize case, ignore blanks
		# In this implementation, the most common values should
		# clearly go at the front of the list
		self.prohibited_values = [x.lower() for x in prohibited_values if x]

	def scan( self, content_fragment ):
		content_fragment = content_fragment.lower()
		#len_content_fragment = len(content_fragment)

		yielded = [] # A simple, inefficient way of making sure we don't send overlapping ranges
		def test(v):
			for t in yielded:
				if v[0] >= t[0] and v[1] <= t[1]:
					return False
			return True

		start_ix = 0
		for x in self.prohibited_values:
			end_ix = content_fragment.find( x, start_ix )
			if end_ix != -1:
				# Got a match
				match_range = (end_ix, end_ix + len(x))
				if test(match_range):
					yielded.append( match_range )
					yield  match_range

@interface.implementer(interfaces.ICensoredContentScanner)
def TrivialMatchScannerExternalFile( file_path ):
	"""
	External files are stored in rot13.
	"""
	# TODO: Does rot13 unicode?
	return TrivialMatchScanner( (x.encode('rot13').strip() for x in open(file_path, 'rU').readlines() ) )

@interface.implementer(interfaces.ICensoredContentScanner)
def DefaultTrivialProfanityScanner():
	return TrivialMatchScannerExternalFile( resource_filename( __name__, 'profanity_list.txt' ) )
