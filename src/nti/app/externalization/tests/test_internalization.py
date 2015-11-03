#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from .. import MessageFactory as _

from hamcrest import raises
from hamcrest import calling
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import contains_string
from nose.tools import assert_raises

from zope import interface
from zope.schema.interfaces import ValidationError

from pyramid import httpexceptions as hexc

from nti.app.externalization import error
from nti.app.externalization import internalization as obj_io

from nti.contentrange import contentrange

from nti.dataserver import contenttypes

from nti.schema.field import Object
from nti.schema.field import ValidTextLine
from nti.schema.field import UniqueIterable

from nti.app.testing.layers import AppLayerTest
from nti.app.testing.request_response import DummyRequest

class TestIO(AppLayerTest):

	def test_read_urlencoded(self):
		request = DummyRequest()
		request.content_type = b'application/x-www-form-urlencoded; charset=UTF-8'

		request.body = b'%7B%22opt_in_email_communication%22%3Atrue%7D='
		assert_that(calling(obj_io.read_body_as_external_object).with_args(request),
					raises(hexc.HTTPBadRequest))

		request.body = b'%7B%22opt_in_email_communication\xe2%22%3Atrue%7D='
		assert_that(calling(obj_io.read_body_as_external_object).with_args(request),
					raises(hexc.HTTPBadRequest))

	def test_integration_note_body_validation_empty_error_message(self):
		n = contenttypes.Note()
		n.applicableRange = contentrange.ContentRangeDescription()
		n.containerId = u'tag:nti:foo'

		with assert_raises(hexc.HTTPUnprocessableEntity) as exc:
			obj_io.update_object_from_external_object(n, { 'body': ['', ''] }, request=DummyRequest())

		assert_that(exc.exception.json_body, has_entry('field', 'body'))

	def test_wrong_contained_type(self):

		class IThing(interface.Interface):
			__name__ = ValidTextLine(title="The name")  # unicode

		@interface.implementer(IThing)
		class Thing(object):
			__name__ = b'not-unicode'

		field = UniqueIterable(
			value_type=Object(IThing, __name__='field'))
		field.__name__ = 'field'

		# So, a set of things having a unicode __name__

		with assert_raises(hexc.HTTPUnprocessableEntity) as exc:
			try:
				field.validate(set([Thing()]))
			except ValidationError as e:
				error.handle_validation_error(DummyRequest(), e)

		assert_that(exc.exception.json_body, has_entry('field', 'field'))
		assert_that(exc.exception.json_body,
					 has_entry('suberrors',
								contains(has_entry('suberrors',
													 contains(has_entries('declared', 'IThing',
																		  'field', '__name__',
																		  'code', 'WrongType'))))))


	def test_translating_non_unicode_bytes_messages(self):

		# This one translates fine
		with assert_raises(hexc.HTTPUnprocessableEntity) as exc:
			try:
				raise ValidationError(b'abcd')
			except ValidationError as e:
				error.handle_validation_error(DummyRequest(), e)

		assert_that(exc.exception.json_body, has_entry('message', 'abcd'))

		# This one does not
		with assert_raises(hexc.HTTPUnprocessableEntity) as exc:
			try:
				raise ValidationError(b'abcd\xff')
			except ValidationError as e:
				error.handle_validation_error(DummyRequest(), e)

		assert_that(exc.exception.json_body, has_entry('message', ''))

	def test_translate(self):
		with assert_raises(hexc.HTTPUnprocessableEntity) as exc:
			try:
				raise ValidationError(b'abcd')
			except ValidationError as e:
				error.raise_json_error(DummyRequest(),
									hexc.HTTPUnprocessableEntity,
									{ 	'message': _("Please provide a valid ${field}.",
													mapping={'field': 'email'}),
									 	'field': 'email',
										'code': e.__class__.__name__ },
									None)

		assert_that(exc.exception.json_body, has_entry('message',
														contains_string('valid email')))

		# Now with non-json
		with assert_raises(hexc.HTTPUnprocessableEntity) as exc:
			try:
				raise ValidationError(b'abcd')
			except ValidationError as e:
				error.raise_json_error(DummyRequest(),
									hexc.HTTPUnprocessableEntity,
									 _("Please provide a valid ${field}.",
													mapping={'field': 'email'}),
									None)

		assert_that(exc.exception.json_body, contains_string('valid email'))
