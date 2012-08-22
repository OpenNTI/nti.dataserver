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
from zope import component

from zope.schema import interfaces as sch_interfaces
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from nti.contentfragments import interfaces

# The algorithms contained in here are trivially simple.
# We could do much better, for example, with prefix trees.
# See https://hkn.eecs.berkeley.edu/~dyoo/python/ahocorasick/
# and http://pypi.python.org/pypi/trie/0.1.1

# If efficiency really matters, and we have many different filters we are
# applying, we would need to do a better job pipelining to avoid copies

def _get_censored_fragment(org_fragment, new_fragment):
	try:
		result = org_fragment.censored( new_fragment )
	except AttributeError:
		result = interfaces.CensoredUnicodeContentFragment( new_fragment )
		interface.alsoProvides( result, interfaces.ICensoredUnicodeContentFragment )
	return result

@interface.implementer(interfaces.ICensoredContentStrategy)
class SimpleReplacementCensoredContentStrategy(object):

	def __init__( self, replacement_char='*' ):
		self.replacement_char = replacement_char
		assert len(self.replacement_char) == 1

	def censor_ranges( self, content_fragment, censored_ranges ):
		# Since we will be replacing each range with its equal length
		# of content and not shortening, then sorting the ranges doesn't matter
		buf = list(content_fragment)

		for start, end in censored_ranges:
			buf[start:end] = self.replacement_char * (end - start)

		new_fragment = ''.join( buf )
		return _get_censored_fragment(content_fragment, new_fragment)

@interface.implementer(interfaces.ICensoredContentScanner)
class TrivialMatchScanner(object):

	def __init__( self, prohibited_values=() ):
		# normalize case, ignore blanks
		# In this implementation, the most common values should
		# clearly go at the front of the list
		self.prohibited_values = [x.lower() for x in prohibited_values if x]

	def _do_scan(self, content_fragment, yielded):
		
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
					
	def scan( self, content_fragment ):
		content_fragment = content_fragment.lower()
		yielded = [] # A simple, inefficient way of making sure we don't send overlapping ranges
		return self._do_scan(content_fragment, yielded)

@interface.implementer(interfaces.ICensoredContentScanner)
def TrivialMatchScannerExternalFile( file_path ):
	"""
	External files are stored in rot13.
	"""
	# TODO: Does rot13 unicode?
	with open(file_path, 'rU') as src:
		return TrivialMatchScanner((x.encode('rot13').strip() for x in src.readlines()))

@interface.implementer(interfaces.ICensoredContentScanner)
class WordMatchScanner(object):

	def __init__( self, words_to_match=() ):
		self.words_to_match = set([x.lower() for x in words_to_match if x]) if words_to_match else ()

	def _do_scan(self, content_fragment):
		for x in self.words_to_match:
			idx = content_fragment.find( x, 0 )
			while (idx != -1):
				match_range = (idx, idx + len(x))
				yield match_range
				idx = content_fragment.find( x, idx + len(x) )
				
	def scan( self, content_fragment ):
		content_fragment = content_fragment.lower()
		return self._do_scan(content_fragment)
		
@interface.implementer(interfaces.ICensoredContentScanner)
class WordPlusTrivialMatchScanner(WordMatchScanner, TrivialMatchScanner):

	def __init__( self, words_to_match=(), prohibited_values=()):
		WordMatchScanner.__init__(self, words_to_match)
		TrivialMatchScanner.__init__(self, prohibited_values)
		
	def scan( self, content_fragment ):
		yielded = []
		content_fragment = content_fragment.lower()
		word_ranges = WordMatchScanner._do_scan(self, content_fragment)
		for match_range in word_ranges:
			yielded.append(match_range)
			yield match_range
			
		trivial_ranges = TrivialMatchScanner._do_scan(self, content_fragment, yielded)
		for match_range in trivial_ranges:
			yield match_range
		
@interface.implementer(interfaces.ICensoredContentScanner)
def ExternalWordPlusTrivialMatchScannerFiles( profanity_path, word_list_path ):
	word_list = (x.strip() for x in open(word_list_path, 'rU').readlines() )
	profanity_list = (x.encode('rot13').strip() for x in open(profanity_path, 'rU').readlines() )
	return WordPlusTrivialMatchScanner(word_list, profanity_list)

@interface.implementer(interfaces.ICensoredContentScanner)
def DefaultTrivialProfanityScanner():
	file_path = resource_filename( __name__, 'profanity_list.txt' )
	return ExternalWordPlusTrivialMatchScannerFiles( file_path, file_path )

@interface.implementer(interfaces.ICensoredContentPolicy)
class DefaultCensoredContentPolicy(object):
	"""
	A content censoring policy that looks up the default
	scanner and strategy and uses them.

	This package does not register this policy as an adapter for anything,
	you must do that yourself.
	"""

	def __init__( self, fragment=None, target=None ):
		pass

	def censor( self, fragment, target ):
		scanner = component.getUtility( interfaces.ICensoredContentScanner )
		strat = component.getUtility( interfaces.ICensoredContentStrategy )

		return strat.censor_ranges( fragment, scanner.scan( fragment ) )


@component.adapter(interfaces.IUnicodeContentFragment, interface.Interface, sch_interfaces.IBeforeObjectAssignedEvent)
def censor_before_object_assigned( fragment, target, event ):
	"""
	Watches for field values to be assigned, and looks for specific policies for the
	given object and field name to handle censoring. If such a policy is found and returns
	something that is not the original fragment, the event is updated (and so the value
	assigned to the target is also updated).
	"""

	if interfaces.ICensoredUnicodeContentFragment.providedBy( fragment ):
		# Nothing to do, already censored
		return

	# Does somebody want to censor assigning values of fragments' type to objects of
	# target's type to the field named event.name?
	policy = component.queryMultiAdapter( (fragment, target),
										  interfaces.ICensoredContentPolicy,
										  name=event.name )
	if policy is not None:
		censored_fragment = policy.censor( fragment, target )
		if censored_fragment != fragment:
			event.object = censored_fragment

from zope.schema._field import BeforeObjectAssignedEvent
from zope.event import notify

def censor_assign( fragment, target, field_name ):
	"""
	Perform manual censoring of assigning an object to a field.
	"""

	evt = BeforeObjectAssignedEvent( fragment, field_name, target )
	notify( evt )
	return evt.object

def _default_profanity_terms():
	file_path = resource_filename( __name__, 'profanity_list.txt' ) 
	with open(file_path, 'rU') as src:
		words = (unicode(x.encode('rot13').strip()) for x in src.readlines() )
	terms = [ SimpleTerm(value=word, token=repr(word)) for word in words ]
	map(lambda x: interface.alsoProvides( x, interfaces.IProfanityTerm ), terms)
	return SimpleVocabulary(terms)
