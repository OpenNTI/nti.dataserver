#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


import unittest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_property

from nti.contentrendering.tests import buildDomFromString, simpleLatexDocumentText
from nti.contentrendering.plastexids import _section_ntiid_filename, _section_ntiid, patch_all

from plasTeX.Context import Context

class IdPatchedLayer(object):

	@classmethod
	def setUp(cls):
		patch_all() # sadly, this is not reversible

	@classmethod
	def tearDown(cls):
		pass

	setUpTest = tearDownTest = tearDown

# For non-layer aware runners...
# this isn't reversible anyway
patch_all()

class TestPlastexIds(unittest.TestCase):

	layer = IdPatchedLayer

	def test_escape_filename(self):
		dom = buildDomFromString( simpleLatexDocumentText(bodies=(r'\chapter{A & () : Chapter}',) ) )

		chapter = dom.getElementsByTagName( 'chapter' )[0]

		assert_that( _section_ntiid_filename( chapter ),
					 is_( 'tag_nextthought_com_2011-10_testing-HTML-temp_a_______chapter' ) )

	def test_case_insensitive_ntiids_collision(self):
		dom = buildDomFromString( simpleLatexDocumentText(bodies=(r'\chapter{A}\chapter{a}',) ) )

		chapter1 = dom.getElementsByTagName( 'chapter' )[0]
		chapter2 = dom.getElementsByTagName( 'chapter' )[1]


		assert_that( _section_ntiid( chapter1 ), is_(  'tag:nextthought.com,2011-10:testing-HTML-temp.a' ) )
		assert_that( _section_ntiid( chapter2 ), is_( 'tag:nextthought.com,2011-10:testing-HTML-temp.a.1' ) )

		assert_that( _section_ntiid_filename( chapter1 ), is_(  'tag_nextthought_com_2011-10_testing-HTML-temp_a' ) )
		assert_that( _section_ntiid_filename( chapter2 ), is_( 'tag_nextthought_com_2011-10_testing-HTML-temp_a_1' ) )


	def test_cross_doc_refs(self):
		dom_str = r'''
		\chapter{A}
		\label{A}
		Some text
		\chapter{B}
		\label{B}
		Some other text
		'''
		dom = buildDomFromString( simpleLatexDocumentText(bodies=(dom_str,) ) )

		chapter1 = dom.getElementsByTagName( 'chapter' )[0]
		chapter2 = dom.getElementsByTagName( 'chapter' )[1]

		chapter1_ntiid = chapter1.ntiid
		chapter2_ntiid = chapter2.ntiid

		bytes_io = dom.context.persist(None)

		context = Context()
		bytes_io.seek(0)

		context.restore(bytes_io)

		assert_that(context.labels, has_entry( 'A', has_property('ntiid', chapter1_ntiid) ))
		assert_that(context.labels, has_entry( 'B', has_property('ntiid', chapter2_ntiid) ))
