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
import nti.contentfragments.schema
import nti.contentfragments.interfaces
from nti.contentfragments.censor import WordMatchScanner
from nti.contentfragments.censor import WordPlusTrivialMatchScanner
from nti.contentfragments.censor import SimpleReplacementCensoredContentStrategy

import nti.tests
from hamcrest import is_
from hamcrest import assert_that

setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.contentfragments,) )

def test_defaults():
	scanner = component.getUtility( nti.contentfragments.interfaces.ICensoredContentScanner )
	strat = component.getUtility( nti.contentfragments.interfaces.ICensoredContentStrategy )

	bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )

	assert_that( strat.censor_ranges( bad_val, scanner.scan( bad_val ) ),
				 is_( 'This is ******* stupid, you ************ *******' ) )

def test_mord_match_scanner():
	wm = WordMatchScanner(['lost','like'])
	bad_val = """So I feel a little like, a child who's lost, a little like, (everything's changed) a
			  lot, I didn't like all of the pain"""

	ranges = list(wm.scan(bad_val))
	assert_that(ranges, is_([(19, 23), (54, 58), (104, 108), (39, 43)]))
	
def test_trivial_and_word_match_scanner():
	
	profanity_file = resource_filename( __name__, '../profanity_list.txt' )
	profanity_list = [x.encode('rot13').strip() for x in open(profanity_file, 'rU').readlines()]

	strat = SimpleReplacementCensoredContentStrategy()	
	scanner = WordPlusTrivialMatchScanner(('stupid',), profanity_list)

	bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )
	assert_that( strat.censor_ranges( bad_val, scanner.scan( bad_val ) ),
				 is_( 'This is ******* ******, you ************ *******' ) )
	
def test_schema_event_censoring():

	class ICensored(interface.Interface):
		body = nti.contentfragments.schema.TextUnicodeContentFragment( title="Body" )

	@interface.implementer(ICensored)
	class Censored(object):
		body = FieldPropertyStoredThroughField(ICensored['body'])

	component.provideAdapter( nti.contentfragments.censor.DefaultCensoredContentPolicy,
							  adapts=(unicode,ICensored),
							  provides=nti.contentfragments.interfaces.ICensoredContentPolicy,
							  name=Censored.body.field.__name__ )

	censored = Censored()

	bad_val = 'Guvf vf shpxvat fghcvq, lbh ZbgureShpxre onfgneq'.encode( 'rot13' )
	bad_val = nti.contentfragments.interfaces.UnicodeContentFragment( bad_val )

	censored.body = bad_val

	assert_that( censored.body,
				 is_( 'This is ******* stupid, you ************ *******' ) )
