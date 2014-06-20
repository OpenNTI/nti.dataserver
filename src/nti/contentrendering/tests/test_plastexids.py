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
from hamcrest import is_not as does_not
from hamcrest import has_entry
from hamcrest import has_property
from hamcrest import contains_string

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

from . import ContentrenderingLayerTest
from . import RenderContext
import os
import io

class TestPlastexIdsRender(ContentrenderingLayerTest):

	def test_cross_doc_ref_links(self):
		source_str = r'''
		\chapter{A}
		\label{A}
		Some text

		\subsection{SubsectionA}
		\label{SubsectionA}
		This is in the same HTML page as the chapter.

		\chapter{B}
		\label{B}
		Some other text \ref{A}.

		\section{SectionB}
		\label{SectionB}
		Some text in subsection that refs \ref{SubsectionA}.

		\begin{equation}
		\label{equation}
			\forall x \in X, \quad \exists y \leq \epsilon
		\end{equation}

		We would like to ref the equation in \ref{equation}.

		\begin{figure}
		\caption{A figure}
		\label{figure} % recall that captions are labeled
		Stuff in figure
		\end{figure}

		We would like to ref the equation in \ref{figure}.
		'''

		ref_str = r'''
		\chapter{One}
		\label{One}
		Back ref to chapter \ntiidref{A}.


		\section{Two}
		Section refs \ntiidref{SectionB}.

		Section also refs \ntiidref{equation}.

		Section also refs \ntiidref{figure}.

		Back ref to subsection \ntiidref{SubsectionA}.

		'''

		source_a_ntiid = "tag:nextthought.com,2011-10:testing-HTML-temp.A"
		source_b_ntiid = "tag:nextthought.com,2011-10:testing-HTML-temp.SectionB"


		with RenderContext(simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.ntilatexmacros}',
															  br'\usepackage{amsmath}'),
													bodies=(source_str,) )) as source_context:

			source_context.render()

			# Our ref should have rendered as a file
			chapter_b = source_context.read_rendered_file('tag_nextthought_com_2011-10_testing-HTML-temp_B.html')
			assert_that( chapter_b,
						 contains_string('href="tag_nextthought_com_2011-10_testing-HTML-temp_A.html"'))

			sec_b = source_context.read_rendered_file('tag_nextthought_com_2011-10_testing-HTML-temp_SectionB.html')
			# check the back-ref to the subsection
			assert_that( sec_b,
						 contains_string('tag_nextthought_com_2011-10_testing-HTML-temp_A.html#SubsectionA'))

			# check the original equation
			assert_that( sec_b,
						 contains_string('id="equation"'))
			# check its reference.
			assert_that( sec_b,
						 contains_string('href="tag_nextthought_com_2011-10_testing-HTML-temp_SectionB.html#equation"'))

			# The ntiid for the equation did not make it into the ToC
			eqn_ntiid = source_context.dom.getElementsByTagName('equation')[0].ntiid
			fig_ntiid = source_context.dom.getElementsByTagName('figure')[0].getElementsByTagName('caption')[0].ntiid
			assert_that( eqn_ntiid, is_('tag:nextthought.com,2011-10:testing-HTMLequation-temp.equation.equation'))
			assert_that( fig_ntiid, is_('tag:nextthought.com,2011-10:testing-HTMLfigure-temp.figure.figure'))
			toc = source_context.read_rendered_file('eclipse-toc.xml')
			for i in eqn_ntiid, fig_ntiid:
				assert_that( toc,
							 does_not( contains_string(i)))

			# Capture the value of the paux file for use later, so
			# we can let this render be completely cleaned up
			with open(os.path.join(source_context.docdir, 'temp.paux'), 'rb') as f:
				paux_value = f.read()

		def load_links(document):
			paux_io = io.BytesIO(paux_value)
			document.context.restore(paux_io,
									 rtype='XHTML')


		with RenderContext(simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.ntilatexmacros}',),
													bodies=(ref_str,)),
						   packages_on_texinputs=True,
						   config_hook=load_links) as ref_context:
			ref_context.render()

			chapter_one = ref_context.read_rendered_file('tag_nextthought_com_2011-10_testing-HTML-temp_One.html')
			section_two = ref_context.read_rendered_file('tag_nextthought_com_2011-10_testing-HTML-temp_Two.html')

			assert_that( chapter_one,
						 contains_string('href="%s"' % source_a_ntiid))

			# Note that the embedded things are referenced
			# by DOM ID relative to the containing ntiid
			for ntiid in source_b_ntiid, source_b_ntiid + '#equation', source_b_ntiid + '#figure', source_a_ntiid + '#SubsectionA':
				assert_that( section_two,
							 contains_string('href="%s"' % ntiid))
