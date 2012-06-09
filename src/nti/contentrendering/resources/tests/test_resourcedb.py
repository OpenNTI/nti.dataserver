#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import os

from hamcrest import assert_that, is_, not_none, same_instance
from hamcrest import contains




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
		self.ctx = RenderContext( simpleLatexDocumentText( bodies=('$x^2$','$f^2', '\[f\]') ) )
		self.ctx.__enter__()

	def tearDown( self ):
		self.ctx.__exit__( None, None, None )
		super(TestResourceDB,self).tearDown()

	def test_system_generate(self):
		# This runs a full test and actually invokes renderers.
		rdb = ResourceDB( self.ctx.dom )
		rdb.generateResourceSets()

		assert_that( rdb.getResource( '$x^2$', ('mathjax_inline',)), is_( not_none() ) )
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
