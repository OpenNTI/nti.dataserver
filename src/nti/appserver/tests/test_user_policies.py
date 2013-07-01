#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import pyPdf
from pyPdf import PdfFileReader

from nti.appserver import user_policies

from nti.appserver.tests.test_application import SharedApplicationTestBase

from hamcrest import (assert_that, is_)

class TestUserPolicies(SharedApplicationTestBase):

	def test__alter_pdf(self):
		stream = user_policies._alter_pdf('coppa_consent_request_email_attachment.pdf', 'myntuser', 'steve', 'parent@nextthought.com')
		pdf_reader=PdfFileReader(stream)
		assert_that(pdf_reader.numPages, is_(1))
		pdf_page = pdf_reader.getPage( 0 )
		page_content = pyPdf.pdf.ContentStream( pdf_page['/Contents'].getObject(), pdf_page.pdf )
		assert_that(page_content.operations[937][0], is_(['myntuser']))
		assert_that(page_content.operations[970][0], is_(['steve']))
		assert_that(page_content.operations[1022][0], is_(['parent@nextthought.com']))