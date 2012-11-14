#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_

from nti.contentrendering.tests import buildDomFromString, simpleLatexDocumentText
from nti.contentrendering.plastexids import _section_ntiid_filename, _section_ntiid, patch_all

setUpModule = patch_all # sadly, this is not reversible


def test_escape_filename():
	dom = buildDomFromString( simpleLatexDocumentText(bodies=(r'\chapter{A & () : Chapter}',) ) )

	chapter = dom.getElementsByTagName( 'chapter' )[0]

	assert_that( _section_ntiid_filename( chapter ),
				 is_( 'tag_nextthought_com_2011-10_testing-HTML-temp_a_______chapter' ) )

def test_case_insensitive_ntiids_collision():
	patch_all()
	dom = buildDomFromString( simpleLatexDocumentText(bodies=(r'\chapter{A}\chapter{a}',) ) )

	chapter1 = dom.getElementsByTagName( 'chapter' )[0]
	chapter2 = dom.getElementsByTagName( 'chapter' )[1]


	assert_that( _section_ntiid( chapter1 ), is_(  'tag:nextthought.com,2011-10:testing-HTML-temp.a' ) )
	assert_that( _section_ntiid( chapter2 ), is_( 'tag:nextthought.com,2011-10:testing-HTML-temp.a.1' ) )

	assert_that( _section_ntiid_filename( chapter1 ), is_(  'tag_nextthought_com_2011-10_testing-HTML-temp_a' ) )
	assert_that( _section_ntiid_filename( chapter2 ), is_( 'tag_nextthought_com_2011-10_testing-HTML-temp_a_1' ) )
