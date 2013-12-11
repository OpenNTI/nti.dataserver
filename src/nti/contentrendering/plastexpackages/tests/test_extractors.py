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
from hamcrest import has_length

from nti.testing import base
from nti.testing import matchers



course_string = r"""
\begin{course}{Law And Justice}{Number}
%Define the Course Discussion Board
\coursecommunity{CLC3403.ou.nextthought.com}
\coursecommunity[scope=restricted]{tag:nextthought.com,2011-10:harp4162-MeetingRoom:Group-clc3403fall2013.ou.nextthought.com}
\courseboard{tag:nextthought.com,2011-10:CLC3403.ou.nextthought.com-Board:GeneralCommunity-DiscussionBoard}
\courseannouncementboard{tag:nextthought.com,2011-10:CLC3403.ou.nextthought.com-Forum:GeneralCommunity-In_Class_Announcements tag:nextthought.com,2011-10:CLC3403.ou.nextthought.com-Forum:GeneralCommunity-Open_Announcements}

%Course Units defined

\end{course}
"""

works_string = r"""
\begin{relatedwork} \label{relwk:AdditionalResources_01.01} \worktitle{1.1 Aristotle}\workcreator{Wikipedia}\worksource{https://en.wikipedia.org/wiki/Aristotle}
Aristotle was a Greek philosopher and polymath, a student of Plato and teacher of Alexander the Great.
\end{relatedwork}
"""

from xml.dom.minidom import parseString
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
	"Does very little verification. Mostly makes sure we don't crash"

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

		assert_that( book.toc.dom.getElementsByTagName('course'), has_length(1) )
		assert_that( book.toc.dom.documentElement.attributes, has_entry('isCourse', 'true'))
		assert_that( book.toc.dom.getElementsByTagNameNS("http://www.nextthought.com/toc", 'related'), has_length(1) )
