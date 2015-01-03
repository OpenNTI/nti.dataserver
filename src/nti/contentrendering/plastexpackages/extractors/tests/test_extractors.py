#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that

import os
import unittest

from xml.dom import minidom

from nti.contentrendering.tests import RenderContext
from nti.contentrendering.tests import simpleLatexDocumentText

from nti.contentrendering.RenderedBook import EclipseTOC
from nti.contentrendering.resources import ResourceRenderer

from nti.contentrendering.plastexpackages.extractors import _CourseExtractor
from nti.contentrendering.plastexpackages.extractors import _RelatedWorkExtractor

from nti.contentrendering.plastexpackages.tests import ExtractorTestLayer

class TestCourseExtractor(unittest.TestCase):

	layer = ExtractorTestLayer

	def test_course_and_related_extractor_works(self):
		# Does very little verification. Mostly makes sure we don't crash
		name = 'sample_course.tex'
		with open(os.path.join( os.path.dirname(__file__), name)) as fp:
			course_string = fp.read()
		name = 'sample_relatedwork.tex'
		with open(os.path.join( os.path.dirname(__file__), name)) as fp:
			works_string = fp.read()
			
		class Book(object):
			toc = None
			document = None
			contentLocation = None
		book = Book()
		
		with RenderContext(simpleLatexDocumentText(
								preludes=("\\usepackage{nticourse}", "\\usepackage{ntilatexmacros}"),
								bodies=(course_string, works_string)),
						   	packages_on_texinputs=True) as ctx:
			book.document = ctx.dom
			book.contentLocation = ctx.docdir

			render = ResourceRenderer.createResourceRenderer('XHTML', None)
			render.render( ctx.dom )
			book.toc = EclipseTOC(os.path.join(ctx.docdir, 'eclipse-toc.xml'))
			course_outline_file = os.path.join(ctx.docdir, 'course_outline.xml')
			ctx.dom.renderer = render

			ext = _CourseExtractor()
			ext.transform(book)

			ext = _RelatedWorkExtractor()
			ext.transform(book)

			__traceback_info__ = book.toc.dom.toprettyxml()

			course_outline = minidom.parse(course_outline_file)

			assert_that(course_outline.getElementsByTagName('course'), has_length(1))
			assert_that(book.toc.dom.documentElement.attributes, has_entry('isCourse', 'true'))
			assert_that(book.toc.dom.getElementsByTagNameNS("http://www.nextthought.com/toc", 'related'),
						has_length(1))

			course = course_outline.getElementsByTagName('course')[0]
			assert_that( course.getElementsByTagName('unit'), has_length(1) )
			unit = course.getElementsByTagName('unit')[0]
			assert_that( unit.attributes, has_entry( 'levelnum', '0'))

			assert_that( unit.getElementsByTagName('lesson'), has_length(5) )
			assert_that( unit.childNodes, has_length(2) )

			assert_that( dict(unit.childNodes[0].attributes.items()),
						 has_entry('isOutlineStubOnly', 'true') )

			lesson = unit.childNodes[1]
			assert_that( dict(lesson.attributes.items()),
						 has_entries( 'levelnum', '1',
									  'date', "2013-08-19T05:00:00Z,2013-08-22T04:59:59Z",
									  'topic-ntiid', "tag:nextthought.com,2011-10:testing-HTML-temp.l2",
									  'isOutlineStubOnly', 'false'))

			sub_lessons = lesson.childNodes
			assert_that( sub_lessons, has_length(1))

			sub_lesson = sub_lessons[0]
			assert_that( dict(sub_lesson.attributes.items()),
						 has_entries( 'levelnum', '2',
									  'date', "2013-12-31T06:00:00Z,2014-01-03T05:59:00Z",
									  'topic-ntiid', "tag:nextthought.com,2011-10:testing-HTML-temp.section_title_2"))

			sub_sub_lessons = sub_lesson.childNodes
			assert_that( sub_sub_lessons, has_length(1))

			sub_sub_lesson = sub_sub_lessons[0]
			assert_that( dict(sub_sub_lesson.attributes.items()),
						 has_entries( 'levelnum', '3',
									  'date', "2014-01-04T05:59:00Z",
									  'topic-ntiid', "tag:nextthought.com,2011-10:testing-HTML-temp.subsection_title_2",
									  'isOutlineStubOnly', 'true'))
