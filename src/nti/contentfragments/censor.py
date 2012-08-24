#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of the content censoring algorithms.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
from collections import defaultdict
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

	def _test_range(self, v, yielded):
		for t in yielded:
			if v[0] >= t[0] and v[1] <= t[1]:
				return False
		return True
		
	def _do_scan(self, content_fragment, yielded):
		for x in self.prohibited_values:
			idx = content_fragment.find( x, 0 )
			while (idx != -1):
				match_range = (idx, idx + len(x))
				if self._test_range(match_range, yielded):
					yield match_range
				idx = content_fragment.find( x, idx + len(x) )
					
	def scan( self, content_fragment ):
		yielded = [] # A simple, inefficient way of making sure we don't send overlapping ranges
		content_fragment = content_fragment.lower()
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
class WordMatchScanner(TrivialMatchScanner):

	_re_word_start    = r"[^\(\"\`{\[:;&\#\*@\)}\]\-,]"

	_re_non_word_chars   = r"(?:[?!)\";}\]\*:@\'\({\[])"

	_re_multi_char_punct = r"(?:\-{2,}|\.{2,}|(?:\.\s){2,}\.)"

	_word_tokenize_fmt = r'''(
		%(MultiChar)s
		|
		(?=%(WordStart)s)\S+?  # Accept word characters until end is found
		(?= # Sequences marking a word's end
		    \s|                                 # White-space
		    $|                                  # End-of-string
		    %(NonWord)s|%(MultiChar)s|          # Punctuation
		    ,(?=$|\s|%(NonWord)s|%(MultiChar)s) # Comma if at end of word
		)
		|
		\S
	)'''

	@classmethod
	def create_word_tokenizer(cls):
		_re_word_tokenizer = re.compile(
				cls._word_tokenize_fmt %
				{
					'NonWord':   cls._re_non_word_chars,
					'MultiChar': cls._re_multi_char_punct,
					'WordStart': cls._re_word_start,
				},
				re.UNICODE | re.VERBOSE
			)
		return _re_word_tokenizer
	
	def __init__( self, white_words=(), prohibited_words=() ):
		self._word_tokenizer = self.create_word_tokenizer()
		self.white_words = set([x.lower() for x in white_words if x]) if white_words else ()
		self.prohibited_words = set([x.lower() for x in prohibited_words if x]) if prohibited_words else ()

	def _do_scan(self, content_fragment, white_words_ranges=[]):
		
		tokens = defaultdict(list)
		for t in self._word_tokenizer.finditer(content_fragment):
			match_range = (t.start(), t.end())
			text = content_fragment[t.start():t.end()]
			tokens[text].append(match_range)

		# save the ranges of safe words
		for word in self.white_words:
			ranges = tokens.get(word, ())
			if ranges:
				white_words_ranges.extend(ranges)
				
		# yield/return any prohibited_words
		for word in self.prohibited_words:
			lst = tokens.get(word, ())
			for match_range in lst:
				if self._test_range(match_range, white_words_ranges):
					yield match_range
				
	def scan( self, content_fragment ):
		content_fragment = content_fragment.lower()
		return self._do_scan(content_fragment)
		
@interface.implementer(interfaces.ICensoredContentScanner)
class WordPlusTrivialMatchScanner(WordMatchScanner):

	def __init__( self, white_words=(), prohibited_words=(), prohibited_values=()):
		WordMatchScanner.__init__(self, white_words, prohibited_words)
		TrivialMatchScanner.__init__(self, prohibited_values)
		
	def scan( self, content_fragment ):
		yielded = []
		white_words_ranges = []
		content_fragment = content_fragment.lower()
		word_ranges = WordMatchScanner._do_scan(self, content_fragment, white_words_ranges)
		for match_range in word_ranges:
			yielded.append(match_range)
			yield match_range
		
		yielded = yielded + white_words_ranges
		trivial_ranges = TrivialMatchScanner._do_scan(self, content_fragment, yielded)
		for match_range in trivial_ranges:
			yield match_range
		
@interface.implementer(interfaces.ICensoredContentScanner)
def ExternalWordPlusTrivialMatchScannerFiles( white_words_path, prohibited_words_path, profanity_path):
	with open(white_words_path, 'rU') as src:
		white_words = (x.strip() for x in src.readlines() )
		
	with open(prohibited_words_path, 'rU') as src:
		prohibited_words = (x.encode('rot13').strip() for x in src.readlines() )
		
	with open(profanity_path, 'rU') as src:
		profanity_list = (x.encode('rot13').strip() for x in src.readlines() )
		
	return WordPlusTrivialMatchScanner(white_words, prohibited_words, profanity_list)

@interface.implementer(interfaces.ICensoredContentScanner)
def DefaultTrivialProfanityScanner():
	white_path = resource_filename( __name__, 'white_list.txt' )
	prohibited_words = resource_filename( __name__, 'prohibited_words.txt' )
	profanity_values = resource_filename( __name__, 'profanity_list.txt' )
	return ExternalWordPlusTrivialMatchScannerFiles( white_path, prohibited_words, profanity_values )

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


