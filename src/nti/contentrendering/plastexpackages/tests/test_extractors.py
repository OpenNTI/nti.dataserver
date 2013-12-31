#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import has_length

from nti.testing import base
from nti.testing import matchers



course_string = r"""
%Course lessons defined

\courselesson{Title 1}{l1} % AKA chapter
\courselessonsection{Section Title 1} % a section
\section{This is ignored}

\courselesson{Title 2}{l2} % another chapter
\section{This is ignored}
\courselessonsection{Section Title 2}{not_before_date=2013-12-31,not_after_date=2014-01-02} % section
\subsection{This Subsection is also ignored}
\courselessonsubsection{SubSection Title 2}{not_after_date=2014-01-03}

% A lesson not included in a unit
\courselesson{Title 3}{l3}


\begin{course}{Law And Justice}{Number}
%Define the Course Discussion Board
\coursecommunity{CLC3403.ou.nextthought.com}
\coursecommunity[scope=restricted]{tag:nextthought.com,2011-10:harp4162-MeetingRoom:Group-clc3403fall2013.ou.nextthought.com}
\courseboard{tag:nextthought.com,2011-10:CLC3403.ou.nextthought.com-Board:GeneralCommunity-DiscussionBoard}
\courseannouncementboard{tag:nextthought.com,2011-10:CLC3403.ou.nextthought.com-Forum:GeneralCommunity-In_Class_Announcements tag:nextthought.com,2011-10:CLC3403.ou.nextthought.com-Forum:GeneralCommunity-Open_Announcements}

%Course units defined

\begin{courseunit}{Unit}
\courselessonref{l1} % no date
\courselessonref{l2}{08/19/2013,08/21/2013} % with date
\end{courseunit}

\end{course}


"""

works_string = r"""
\begin{relatedwork} \label{relwk:AdditionalResources_01.01} \worktitle{1.1 Aristotle}\workcreator{Wikipedia}\worksource{https://en.wikipedia.org/wiki/Aristotle}
Aristotle was a Greek philosopher and polymath, a student of Plato and teacher of Alexander the Great.
\end{relatedwork}
"""

from nti.contentrendering.tests import RenderContext
from nti.contentrendering.tests import simpleLatexDocumentText

import os.path

from ..extractors import _CourseExtractor
from ..extractors import _RelatedWorkExtractor
from nti.contentrendering.RenderedBook import EclipseTOC
from nti.contentrendering.resources import ResourceRenderer

# Nose module-level setup and teardown
import nti.testing.base
setUpModule = lambda: nti.testing.base.module_setup( set_up_packages=('nti.contentrendering',__name__,'nti.assessment','nti.externalization') )
tearDownModule = nti.testing.base.module_teardown



def test_course_and_related_extractor_works():
	#Does very little verification. Mostly makes sure we don't crash

	class Book(object):
		document = None
		toc = None
		contentLocation = None

	book = Book()

	with RenderContext(simpleLatexDocumentText( preludes=("\\usepackage{nticourse}","\\usepackage{ntilatexmacros}"),
												bodies=(course_string,works_string)),
					   packages_on_texinputs=True) as ctx:
		book.document = ctx.dom
		book.contentLocation = ctx.docdir

		render = ResourceRenderer.createResourceRenderer('XHTML', None)
		render.render( ctx.dom )
		book.toc = EclipseTOC(os.path.join(ctx.docdir, 'eclipse-toc.xml'))
		ctx.dom.renderer = render

		ext = _CourseExtractor()
		ext.transform(book)

		ext = _RelatedWorkExtractor()
		ext.transform(book)

		__traceback_info__ = book.toc.dom.toprettyxml()

		assert_that( book.toc.dom.getElementsByTagName('course'), has_length(1) )
		assert_that( book.toc.dom.documentElement.attributes, has_entry('isCourse', 'true'))
		assert_that( book.toc.dom.getElementsByTagNameNS("http://www.nextthought.com/toc", 'related'), has_length(1) )

		course = book.toc.dom.getElementsByTagName('course')[0]
		assert_that( course.getElementsByTagName('unit'), has_length(1) )
		unit = course.getElementsByTagName('unit')[0]
		assert_that( unit.attributes, has_entry( 'levelnum', '0'))

		assert_that( unit.getElementsByTagName('lesson'), has_length(5) )
		assert_that( unit.childNodes, has_length(2) )

		lesson = unit.childNodes[1]
		assert_that( dict(lesson.attributes.items()),
					 has_entries( 'levelnum', '1',
								  'date', "2013-08-19T05:00:00+00:00,2013-08-22T04:59:59.999999+00:00",
								  'topic-ntiid', "tag:nextthought.com,2011-10:testing-HTML-temp.l2"))


		sub_lessons = lesson.childNodes
		assert_that( sub_lessons, has_length(1))

		sub_lesson = sub_lessons[0]
		assert_that( dict(sub_lesson.attributes.items()),
					 has_entries( 'levelnum', '2',
								  'date', "2013-12-31T06:00:00+00:00,2014-01-02T06:00:00+00:00",
								  'topic-ntiid', "tag:nextthought.com,2011-10:testing-HTML-temp.section_title_2"))

		sub_sub_lessons = sub_lesson.childNodes
		assert_that( sub_sub_lessons, has_length(1))

		sub_sub_lesson = sub_sub_lessons[0]
		assert_that( dict(sub_sub_lesson.attributes.items()),
					 has_entries( 'levelnum', '3',
								  'date', "2014-01-03T06:00:00+00:00",
								  'topic-ntiid', "tag:nextthought.com,2011-10:testing-HTML-temp.subsection_title_2"))
