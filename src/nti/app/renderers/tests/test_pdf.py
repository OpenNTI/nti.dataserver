#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import starts_with

from pyramid.renderers import render

from nti.app.testing.application_webtest import ApplicationLayerTest

class TestPDFRender(ApplicationLayerTest):
	
	no_cache = False

	def test_render(self):
		# Fix up the dummy request
		self.request.pragma = None
		self.request.cache_control = self
		self.request.accept_encoding = None
		self.request.if_none_match = False
		result = render( "test_pdf_template.rml",
						 {'username': 'foo@bar', 'realname': 'Snoop Dogg', 'email': 'foo@bar'},
						 request=self.request )


		assert_that( result, starts_with(b'%PDF-1.4'))
		del self.request.cache_control # break cycle
