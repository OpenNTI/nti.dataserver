#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_

from . import buildDomFromString, simpleLatexDocumentText
from nti.contentrendering.plastexids import _section_ntiid_filename, _section_ntiid

def test_escape_filename():
	dom = buildDomFromString( simpleLatexDocumentText(bodies=(r'\chapter{A & () : Chapter}',) ) )

	chapter = dom.getElementsByTagName( 'chapter' )[0]

	chapter._ntiid_get_local_part = chapter.title.textContent

	chapter.ntiid = _section_ntiid( chapter )

	assert_that( _section_ntiid_filename( chapter ),
				 is_( 'tag_nextthought_com_2011-10_testing-HTML-temp_a_______chapter' ) )
