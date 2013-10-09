#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import PyPDF2 as pyPdf

from .. import user_policies

from nti.appserver.tests.test_application import SharedApplicationTestBase

from hamcrest import (assert_that, is_)

class TestUserPolicies(SharedApplicationTestBase):

	def test__alter_pdf(self):
		stream = user_policies._alter_pdf('coppa_consent_request_email_attachment.pdf',
										  'supportmathcoppa69', 'Greg', 'greg.higgins@nextthought.com')
		pdf_reader = pyPdf.PdfFileReader(stream)
		assert_that(pdf_reader.numPages, is_(1))
		pdf_page = pdf_reader.getPage(0)
		page_content = pyPdf.pdf.ContentStream(pdf_page['/Contents'].getObject(), pdf_page.pdf)
		assert_that(page_content.operations[382][0], is_(['supportmathcoppa69']))
		assert_that(page_content.operations[401][0], is_(['Greg']))
		assert_that(page_content.operations[424][0], is_(['greg.higgins@nextthought.com']))

	def test__alter_pdf_visual_glitch_on_j(self):
		# No real verification , just an easy way to check on the visual glitches
		# Test with long and short first names
		stream = user_policies._alter_pdf('coppa_consent_request_email_attachment.pdf',
										  'supportmathcoppa69', 'Christopher', 'jason_madden@nextthought-com')
		#with open('/tmp/NEW.pdf', 'wb') as f:
		#	f.write( stream.getvalue() )
		pdf_reader = pyPdf.PdfFileReader(stream)
		assert_that(pdf_reader.numPages, is_(1))
		pdf_page = pdf_reader.getPage(0)
		page_content = pyPdf.pdf.ContentStream(pdf_page['/Contents'].getObject(), pdf_page.pdf)
		assert_that(page_content.operations[382][0], is_(['supportmathcoppa69']))
		assert_that(page_content.operations[401][0], is_(['Christopher']))
		assert_that(page_content.operations[424][0], is_(['jason_madden@nextthought-com']))
