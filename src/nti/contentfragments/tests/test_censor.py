#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField

from pkg_resources import resource_filename

import nti.contentfragments
from nti.contentfragments import censor as frag_censor
from nti.contentfragments import schema as frag_schema
from nti.contentfragments import interfaces as frag_interfaces

import nti.tests
from hamcrest import is_
from hamcrest import assert_that

# nose module-level setup
setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.contentfragments,) )
tearDownModule = nti.tests.module_teardown


def test_defaults():
	scanner = component.getUtility( frag_interfaces.ICensoredContentScanner )
	strat = component.getUtility( frag_interfaces.ICensoredContentStrategy )

	bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )
	assert_that( strat.censor_ranges( bad_val, scanner.scan( bad_val ) ),
				 is_( 'This is ******* stupid, you ************ *******' ) )

def test_mike_words():
	scanner = component.getUtility( frag_interfaces.ICensoredContentScanner )
	strat = component.getUtility( frag_interfaces.ICensoredContentStrategy )

	bad_val = 'ubefrfuvg'.encode( 'rot13' )
	assert_that( strat.censor_ranges( bad_val, scanner.scan( bad_val ) ),
				 is_( '*********' ) )

	bad_val = 'ohyyfuvg'.encode( 'rot13' )
	assert_that( strat.censor_ranges( bad_val, scanner.scan( bad_val ) ),
				 is_( '********' ) )

	bad_val = 'nffbpvngrq cerff'.encode( 'rot13' )
	assert_that( strat.censor_ranges( bad_val, scanner.scan( bad_val ) ),
				 is_( 'associated press' ) )

def test_kaley_words():
	scanner = component.getUtility( frag_interfaces.ICensoredContentScanner )
	strat = component.getUtility( frag_interfaces.ICensoredContentStrategy )
	vals = "Manuscript, proclamation, grasses, endorsement, passes, hoarse  safeguard, farther, seashore shore ashore, glasses"
	assert_that( strat.censor_ranges( vals, scanner.scan( vals ) ),
				 is_( vals ) )

def test_word_match_scanner():
	wm = frag_censor.WordMatchScanner((), ['lost','like'])
	bad_val = """So I feel a little like, a child who's lost, a little like, (everything's changed) a
			  lot, I didn't like all of the pain"""

	ranges = list(wm.scan(bad_val))
	assert_that(ranges, is_([(39, 43), (19, 23), (54, 58), (104, 108)]))

	wm = frag_censor.WordMatchScanner((), ['thought'])
	ranges = list(wm.scan(bad_val))
	assert_that(ranges, is_([]))

	wm = frag_censor.WordMatchScanner(('lost',), ['lost','like'])
	ranges = list(wm.scan(bad_val))
	assert_that(ranges, is_([(19, 23), (54, 58), (104, 108)]))

	bad_val = "So I am a rock on!!! forever"
	wm = frag_censor.WordMatchScanner((), ['rock on','apple'])
	ranges = list(wm.scan(bad_val))
	assert_that(ranges, is_([(10,17)]))
	bad_val = "So I am a rock one and that is it"
	ranges = list(wm.scan(bad_val))
	assert_that(ranges, is_([]))

	bad_val = "buck bill gates"
	wm = frag_censor.WordMatchScanner((), ['buck'])
	ranges = list(wm.scan(bad_val))
	assert_that(ranges, is_([(0,4)]))

	bad_val = "buck bill gates"
	wm = frag_censor.WordMatchScanner((), ['gates'])
	ranges = list(wm.scan(bad_val))
	assert_that(ranges, is_([(10,15)]))

def test_pipeline_scanner():
	profanity_file = resource_filename( __name__, '../profanity_list.txt' )
	with open(profanity_file, 'rU') as f:
		profanity_list = {x.encode('rot13').strip() for x in f.readlines()}

	scanners = []
	scanners.append(frag_censor.WordMatchScanner((), ('stupid',)))
	scanners.append(frag_censor.TrivialMatchScanner(profanity_list))
	scanner = frag_censor.PipeLineMatchScanner(scanners)

	strat = frag_censor.SimpleReplacementCensoredContentStrategy()

	bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )
	assert_that( strat.censor_ranges( bad_val, scanner.scan( bad_val ) ),
				 is_( 'This is ******* ******, you ************ *******' ) )

	bad_val = 'ohggre pbafgvghgvba pbzchgngvba'.encode( 'rot13' )
	assert_that( strat.censor_ranges( bad_val, scanner.scan( bad_val ) ),
				 is_( 'butter constitution computation' ) )

def test_regexp_match_scanner():
	profanity_file = resource_filename( __name__, '../profanity_regexp_list.txt' )
	with open(profanity_file, 'rU') as f:
		profanity_list = {x.encode('rot13').strip() for x in f.readlines()}
	strat = frag_censor.RegExpMatchScanner(words=profanity_list)

	bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )
	ranges = strat.sort_ranges(strat.scan(bad_val))
	assert_that(ranges, is_([(8, 12), (28, 38), (34, 38), (41, 48)]))

def test_html_and_default_policy():
	policy = frag_censor.DefaultCensoredContentPolicy()
	template = '<html><head/><body><b>%s</b></body></html>'
	for w in ('shpx', 'penc'):
		bad_val = template % w.encode( 'rot13' )
		bad_val =  frag_interfaces.HTMLContentFragment(bad_val)
		assert_that(policy.censor(bad_val, None),
				 	is_( '<html><head/><body><b>****</b></body></html>' ) )

def test_schema_event_censoring():

	class ICensored(interface.Interface):
		body = frag_schema.TextUnicodeContentFragment( title="Body" )

	@interface.implementer(ICensored)
	class Censored(object):
		body = FieldPropertyStoredThroughField(ICensored['body'])

	component.provideAdapter( frag_censor.DefaultCensoredContentPolicy,
							  adapts=(unicode,ICensored),
							  provides=frag_interfaces.ICensoredContentPolicy,
							  name=Censored.body.field.__name__ )

	censored = Censored()

	bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )
	bad_val = frag_interfaces.UnicodeContentFragment( bad_val )

	censored.body = bad_val

	assert_that( censored.body,
				 is_( 'This is ******* stupid, you ************ *******' ) )
