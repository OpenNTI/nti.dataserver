#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
algorithms for content censoring.

The algorithms contained in here are trivially simple.
We could do much better, for example, with prefix trees.
See https://hkn.eecs.berkeley.edu/~dyoo/python/ahocorasick/
and http://pypi.python.org/pypi/trie/0.1.1

If efficiency really matters, and we have many different filters we are
applying, we would need to do a better job pipelining to avoid copies

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import array
from pkg_resources import resource_filename

import html5lib
from lxml import etree
from html5lib import treebuilders

from zope import interface
from zope import component
from zope.event import notify

from . import interfaces

from nti.utils.property import Lazy

def punkt_re_char(lang='en'):
	# TODO: remove circular dependency, content processing uses content fragments
	from nti.contentprocessing import interfaces as cp_interfaces
	return component.getUtility(cp_interfaces.IPunctuationCharExpressionPlus, name=lang)

def _get_censored_fragment(org_fragment, new_fragment, factory=interfaces.CensoredUnicodeContentFragment):
	try:
		result = org_fragment.censored(new_fragment)
	except AttributeError:
		result = factory(new_fragment)
		if not interfaces.ICensoredUnicodeContentFragment.providedBy(result):
			interface.alsoProvides(result, interfaces.ICensoredUnicodeContentFragment)
	return result

@interface.implementer(interfaces.ICensoredContentStrategy)
class SimpleReplacementCensoredContentStrategy(object):

	def __init__(self, replacement_char='*'):
		assert len(replacement_char) == 1
		self._replacement_array = array.array(b'u', replacement_char)

	def censor_ranges(self, content_fragment, censored_ranges):
		# Since we will be replacing each range with its equal length
		# of content and not shortening, then sorting the ranges doesn't matter
		content_fragment = content_fragment.decode('utf-8') if isinstance(content_fragment, bytes) else content_fragment
		buf = array.array(b'u', content_fragment)

		for start, end in censored_ranges:
			buf[start:end] = self._replacement_array * (end - start)

		new_fragment = buf.tounicode()
		return _get_censored_fragment(content_fragment, new_fragment)

class BasicScanner(object):

	def sort_ranges(self, ranges):
		return sorted(ranges)

	def test_range(self, new_range, yielded):
		for t in yielded:
			if new_range[0] >= t[0] and new_range[1] <= t[1]:
				# new_range is entirely included in something we already yielded
				return False
		return True

	def do_scan(self, fragment, ranges):
		raise NotImplementedError()

	def scan(self, content_fragment):
		yielded = []  # A simple, inefficient way of making sure we don't send overlapping ranges
		content_fragment = content_fragment.lower()
		return self.do_scan(content_fragment, yielded)

@interface.implementer(interfaces.ICensoredContentScanner)
class TrivialMatchScanner(BasicScanner):

	def __init__(self, prohibited_values=()):
		# normalize case, ignore blanks
		# In this implementation, the most common values should
		# clearly go at the front of the list
		self.prohibited_values = [x.lower() for x in prohibited_values if x]

	def do_scan(self, content_fragment, yielded):
		for the_word in self.prohibited_values:
			# Find all occurrences of each prohibited word,
			# one at a time
			idx = content_fragment.find(the_word, 0)
			while idx != -1:
				match_range = (idx, idx + len(the_word))
				if self.test_range(match_range, yielded):
					yield match_range
				idx = content_fragment.find(the_word, match_range[1])

@interface.implementer(interfaces.ICensoredContentScanner)
class WordMatchScanner(BasicScanner):

	def __init__(self, white_words=(), prohibited_words=()):
		self.white_words = tuple([word.lower() for word in white_words])
		self.prohibited_words = tuple([word.lower() for word in prohibited_words])

	@Lazy
	def char_tester(self):
		return re.compile(punkt_re_char())

	def _test_start(self, idx, content_fragment):
		result = idx == 0 or self.char_tester.match(content_fragment[idx - 1])
		return result

	def _test_end(self, idx, content_fragment):
		result = idx == len(content_fragment) or self.char_tester.match(content_fragment[idx])
		return result

	def _find_ranges(self, word_list, content_fragment):
		for the_word in word_list: # Find all occurrences of each word one by one
			idx = content_fragment.find(the_word, 0)
			while idx != -1:
				endidx = idx + len(the_word)
				match_range = (idx, endidx)
				if self._test_start(idx, content_fragment) and self._test_end(endidx, content_fragment):
					yield match_range
				idx = content_fragment.find(the_word, endidx)

	def do_scan(self, content_fragment, yielded):
		# Here, 'yielded' is the ranges we examine and either guarantee
		# they are good, or guarantee they are bad
		ranges = self._find_ranges(self.white_words, content_fragment)
		yielded.extend(ranges)

		# yield/return any prohibited_words
		ranges = self._find_ranges(self.prohibited_words, content_fragment)
		for match_range in ranges:
			if self.test_range(match_range, yielded):
				yield match_range

@interface.implementer(interfaces.ICensoredContentScanner)
class PipeLineMatchScanner(BasicScanner):

	def __init__(self, scanners=()):
		self.scanners = tuple(scanners)

	def do_scan(self, content_fragment, yielded):
		content_fragment = content_fragment.lower()
		for s in self.scanners:
			matched_ranges = s.do_scan(content_fragment, yielded)
			for match_range in matched_ranges:
				if self.test_range( match_range, yielded ):
					yield match_range

@interface.implementer(interfaces.ICensoredContentScanner)
def _word_profanity_scanner():
	"""
	External files are stored in rot13.
	"""
	white_words_path = resource_filename(__name__, 'white_list.txt')
	prohibited_words_path = resource_filename(__name__, 'prohibited_words.txt')

	with open(white_words_path, 'rU') as src:
		white_words = {x.strip().lower() for x in src.readlines()}

	with open(prohibited_words_path, 'rU') as src:
		prohibited_words = {x.encode('rot13').strip().lower() for x in src.readlines()}

	return WordMatchScanner(white_words, prohibited_words)

@interface.implementer(interfaces.ICensoredContentScanner)
def _word_plus_trivial_profanity_scanner():
	profanity_list_path = resource_filename(__name__, 'profanity_list.txt')
	with open(profanity_list_path, 'rU') as src:
		profanity_list = {x.encode('rot13').strip().lower() for x in src.readlines()}
	return PipeLineMatchScanner([_word_profanity_scanner(), TrivialMatchScanner(profanity_list)])

@interface.implementer(interfaces.ICensoredContentPolicy)
class DefaultCensoredContentPolicy(object):
	"""
	A content censoring policy that looks up the default
	scanner and strategy and uses them.

	This package does not register this policy as an adapter for anything,
	you must do that yourself.
	"""

	def __init__(self, fragment=None, target=None):
		pass

	def censor(self, fragment, target):
		if interfaces.IHTMLContentFragment.providedBy(fragment):
			result = self.censor_html(fragment, target)
		else:
			result = self.censor_text(fragment, target)
		return result

	def censor_text(self, fragment, target):
		scanner = component.getUtility(interfaces.ICensoredContentScanner)
		strat = component.getUtility(interfaces.ICensoredContentStrategy)
		return strat.censor_ranges(fragment, scanner.scan(fragment))

	def censor_html(self, fragment, target):
		result = None
		try:
			p = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
			doc = p.parse(fragment)
			for node in doc.iter():
				for name in ('text', 'tail'):
					text = getattr(node, name, None)
					if text:
						text = self.censor_text(interfaces.UnicodeContentFragment(text), target)
						setattr(node, name, text)

			docstr = unicode(etree.tostring(doc))
			# be sure to return the best interface
			result = _get_censored_fragment(fragment, docstr, interfaces.CensoredHTMLContentFragment)
		except Exception:  # TODO: What exception?
			result = self.censor_text(fragment, target)
		return result


from nti.utils.schema import BeforeTextAssignedEvent

def censor_before_text_assigned(fragment, target, event):
	"""
	Watches for field values to be assigned, and looks for specific policies for the
	given object and field name to handle censoring. If such a policy is found and returns
	something that is not the original fragment, the event is updated (and so the value
	assigned to the target is also updated).
	"""

	if interfaces.ICensoredUnicodeContentFragment.providedBy(fragment):
		# Nothing to do, already censored
		return None, None

	# Does somebody want to censor assigning values of fragments' type to objects of
	# target's type to the field named event.name?
	policy = component.queryMultiAdapter((fragment, target),
										  interfaces.ICensoredContentPolicy,
										  name=event.name)
	if policy is not None:
		censored_fragment = policy.censor(fragment, target)
		if censored_fragment is not fragment and censored_fragment != fragment:
			event.object = censored_fragment

			# notify censoring
			context = event.context or target
			notify(interfaces.CensoredContentEvent(fragment, censored_fragment, event.name, context))

			# as an optimization when we are called directly
			return event.object, True

	return fragment, False

def censor_before_assign_components_of_sequence(sequence, target, event):
	"""
	Register this adapter for (usually any) sequence, some specific interface target, and
	the :class:`nti.utils.schema.IBeforeSequenceAssignedEvent` and it will
	iterate across the fields and attempt to censor each of them.

	This package DOES NOT register this event.
	"""
	if sequence is None:
		return

	# There are many optimization opportunities here
	s2 = []
	_changed = False
	evt = BeforeTextAssignedEvent(None, event.name, event.context)
	for obj in sequence:
		evt.object = obj
		val, changed = censor_before_text_assigned(obj, target, evt)
		_changed |= changed
		s2.append(val)

	# only copy the list/tuple/whatever if we need to
	if _changed:
		event.object = type(event.object)(s2)


def censor_assign(fragment, target, field_name):
	"""
	Perform manual censoring of assigning an object to a field.
	"""
	evt = BeforeTextAssignedEvent(fragment, field_name, target)
	return censor_before_text_assigned(fragment, target, evt)[0]
