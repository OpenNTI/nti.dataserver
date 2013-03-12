#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from zope import interface
from zope.schema.interfaces import ValidationError

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import contains
from hamcrest import has_entries
from nose.tools import assert_raises

import nti.tests
from . import DummyRequest

from nti.appserver import _external_object_io as obj_io
from nti.appserver import httpexceptions as hexc

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.appserver',) )
tearDownModule = nti.tests.module_teardown

from nti.contentrange import contentrange
from nti.dataserver import contenttypes
from nti.utils import schema

def test_integration_note_body_validation_empty_error_message():
	n = contenttypes.Note()
	n.applicableRange = contentrange.ContentRangeDescription()
	n.containerId = u'tag:nti:foo'

	with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
		obj_io.update_object_from_external_object( n, { 'body': ['',''] }, request=DummyRequest() )


	assert_that( exc.exception.json_body, has_entry( 'field', 'body' ) )

def test_wrong_contained_type():

	class IThing(interface.Interface):
		__name__ = schema.ValidTextLine(title="The name") # unicode

	@interface.implementer(IThing)
	class Thing(object):
		__name__ = b'not-unicode'

	field = schema.UniqueIterable(
		value_type=schema.Object(IThing, __name__='field'))
	field.__name__ = 'field'

	# So, a set of things having a unicode __name__

	with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
		try:
			field.validate( set([Thing()]) )
		except ValidationError as e:
			obj_io.handle_validation_error( DummyRequest(), e )

	assert_that( exc.exception.json_body, has_entry( 'field', 'field' ) )
	assert_that( exc.exception.json_body, has_entry( 'suberrors', contains( has_entry( 'suberrors', contains( has_entries( 'declared', 'IThing', 'field', '__name__', 'code', 'WrongType' ) ) ) ) ) )
