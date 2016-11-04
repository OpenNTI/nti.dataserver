#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import not_none
from hamcrest import assert_that

from nti.externalization import internalization

from nti.app.mail.interfaces import Email

from . import MailLayerTest

class TestExternalization(MailLayerTest):

	def test_internalize(self):
		body = 'This is the email text body.'
		subject = 'Email Subject'
		mail = {'MimeType': Email.mime_type,
				'Body': body,
				'Subject': subject,
				'NoReply': True,
				'Copy': True }

		factory = internalization.find_factory_for(mail)
		assert_that(factory, not_none())

		# Basic
		new_io = factory()
		internalization.update_from_external_object(new_io, mail)
		assert_that( new_io.Body, is_( body ))
		assert_that( new_io.Subject, is_( subject ))
		assert_that( new_io.NoReply, is_( True ))
		assert_that( new_io.Copy, is_( True ))

		# Without optionals
		mail.pop( 'NoReply' )
		mail.pop( 'Subject' )
		mail.pop( 'Copy' )
		new_io = factory()
		internalization.update_from_external_object(new_io, mail)
		assert_that( new_io.Body, is_( body ))
		assert_that( new_io.NoReply, is_( False ))
		assert_that( new_io.Copy, is_( False ))

