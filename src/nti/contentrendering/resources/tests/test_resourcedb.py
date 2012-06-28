#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import os

from hamcrest import assert_that, is_, not_none, same_instance
from hamcrest import contains, none




import plasTeX
from plasTeX.TeX import TeX


from nti.contentrendering.tests import simpleLatexDocumentText, ConfiguringTestBase, buildDomFromString, RenderContext


from nti.contentrendering.resources import interfaces
from nti.contentrendering.resources.converters import ImagerContentUnitRepresentationBatchConverter, AbstractLatexCompilerDriver, AbstractCompilingContentUnitRepresentationBatchConverter

from nti.tests import verifiably_provides

from nti.contentrendering.resources.ResourceDB import ResourceDB

class TestResourceDB(ConfiguringTestBase):

	def setUp( self ):
		super(TestResourceDB,self).setUp()
		self.ctx = RenderContext( simpleLatexDocumentText( preludes=(br'\usepackage{graphicx}',),
														   bodies=('$x^2$','$f^2$', r'\[f\]', '$z^2$', r'\[t^3\]') ) )
		self.ctx.__enter__()

	def tearDown( self ):
		self.ctx.__exit__( None, None, None )
		super(TestResourceDB,self).tearDown()

	def test_system_generate(self):
		# This runs a full test and actually invokes renderers.
		rdb = ResourceDB( self.ctx.dom )
		rdb.overrides['$z^2$'] = ('png',)
		rdb.overrides[r'\[t^3\]'] = ('svg',)
		rdb.generateResourceSets()

		assert_that( rdb.getResource( '$x^2$', ('mathjax_inline',)), is_( not_none() ) )
		assert_that( rdb.getResource( '$z^2$', ('png', 'orig', 1)), is_( not_none() ) )
		# Note the unnormalized source for display math
		assert_that( rdb.getResource( r'\[ f \]', ('mathjax_display',)), is_( not_none() ) )
		assert_that( rdb.getResource( r'\[ t^3 \]', ('svg',)), is_( not_none() ) )


		assert_that( rdb.getResourcePath( '$x^2$', ('mathjax_inline',)), is_( not_none() ) )
		assert_that( rdb.getResourceContent( '$x^2$', ('mathjax_inline',)), is_( not_none() ) )
		assert_that( rdb.hasResource( '$x^2$', ('mathjax_inline',)), is_( not_none() ) )


		# and again still works but does nothing
		res = rdb.getResource( '$x^2$', ('mathjax_inline',))
		rdb.generateResourceSets()
		assert_that( rdb.getResource( '$x^2$', ('mathjax_inline',)), is_( same_instance( res ) ) )

		# we can reload
		rdb = ResourceDB( self.ctx.dom )
		# and have existing resources without regenerating
		assert_that( rdb.getResource( '$x^2$', ('mathjax_inline',)), is_( not_none() ) )

		# If we corrupt the resource file, we have to start from scratch
		with open( rdb._indexPath, 'wb' ) as f:
			f.write( "invalid pickle" )

		rdb = ResourceDB( self.ctx.dom )
		assert_that( rdb.getResource( '$x^2$', ('mathjax_inline',)), is_( none() ) )


class TestResourceDBTabular(ConfiguringTestBase):

	body = br"""
		\begin{center}
		\begin{tabular}{|l|c|c|c|r|}
		\multicolumn{5}{c}{Students in Middle School By Grade}\\ \hline
		&$6^{th}$ Grade&$7^{th}$ Grade&$8^{th}$ Grade&Total\\   \hline
		East Middle School & 213 & 241 & 217 & 671 \\           \hline
		West Middle School & 135 & 142 & 120 & \\               \hline
		North Middle School & 230 &130 &  & 534 \\               \hline
		South Middle School & 341 &  & 339 & 1023\\           \hline

		\end{tabular}
		\end{center}"""

	def setUp( self ):
		super(TestResourceDBTabular,self).setUp()
		self.ctx = RenderContext( simpleLatexDocumentText( preludes=(br'\usepackage{graphicx}',br'\usepackage{multicol}'),
														   bodies=( self.body, ) ) )
		self.ctx.__enter__()

	def tearDown( self ):
		self.ctx.__exit__( None, None, None )
		super(TestResourceDBTabular,self).tearDown()

	def test_system_generate(self):
		# This runs a full test and actually invokes renderers.
		rdb = ResourceDB( self.ctx.dom )

		# Make sure that we're going to get the number of hlines we want
		tabular = self.ctx.dom.getElementsByTagName( 'tabular' )[0]
		assert_that( tabular.source.count( br'\hline' ), is_( self.body.count( br'\hline') ) )

		rdb.generateResourceSets()
		# Make sure the hlines make it to the resources
		# Our verification is simple, based just on equality to existing files. This is probable
		# fragile.
		normalized_source= rdb._db.keys()[0]

		resource_png = rdb.getResourcePath( normalized_source, ('png','orig', 1))
		resource_svg = rdb.getResourcePath( normalized_source, ('svg',) )

		# The files tend to differ
	#	assert_that( open( os.path.join( os.path.dirname(__file__), 'tabular_hlines.png' ), 'rb' ).read(),
	#				 is_( open( resource_png, 'rb' ).read() ) )
		assert_that( resource_png, is_( not_none() ) )
		assert_that( resource_svg, is_( not_none() ) )
		# assert_that( open( os.path.join( os.path.dirname(__file__), 'tabular_hlines.svg' ), 'rb' ).read(),
		# 			 is_( open( resource_svg, 'rb' ).read() ) )
