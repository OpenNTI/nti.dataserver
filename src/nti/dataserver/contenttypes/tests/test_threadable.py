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
from nti.dataserver import interfaces as nti_interfaces

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_entry

import nti.tests

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver','nti.contentrange','nti.contentfragments') )
tearDownModule = nti.tests.module_teardown

from nti.dataserver.contenttypes import Note as _Note
from nti.contentrange.contentrange import ContentRangeDescription
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object


class _Mutable_P_Mtime_Note(_Note):
	_p_mtime = None

def Note():
	n = _Mutable_P_Mtime_Note()
	n.applicableRange = ContentRangeDescription()
	return n

from nti.dataserver.intid_wref import WeakRef
class ReferenceObject(WeakRef):
	# Extend the real ref, to get its implementation,
	# but override the moving parts

	__slots__ = ('external_ntiid_oid', 'ref_is_deleted', 'creator', 'sharingTargets')

	def __init__( self ):
		# deliberately not calling super
		self._entity_id = 1
		self.external_ntiid_oid = 'abc'
		self.ref_is_deleted = False

	def __call__(self):
		if not self.ref_is_deleted:
			return self

	def to_external_ntiid_oid( self ):
		return self.external_ntiid_oid

def test_write_external_reply_to():
	top = ReferenceObject()
	note = Note()
	note.inReplyTo = top

	ext = to_external_object( note )

	assert_that( ext, has_entry( 'inReplyTo', 'abc' ) )
	assert_that( ext, has_entry( 'references', [] ) )

def test_write_external_reply_to_deleted():
	top = ReferenceObject()
	child = ReferenceObject()
	child._entity_id = 2

	note = Note()
	note.inReplyTo = child
	note.addReference( top )

	child.ref_is_deleted = True
	top.ref_is_deleted = True
	ext = to_external_object( note )

	assert_that( ext, has_entry( 'inReplyTo', 'tag:nextthought.com,2011-10:Missing-x' ) )
	assert_that( ext, has_entry( 'references', ['tag:nextthought.com,2011-10:Missing-y'] ) )


def test_update_external_reply_to():
	top = ReferenceObject()
	note = Note()

	ext = to_external_object( note )
	ext['applicableRange'] = ContentRangeDescription()

	ext['inReplyTo'] = top
	top.sharingTargets = () # required by note's first update
	top.creator = None
	update_from_external_object( note, ext )

	assert_that( note.inReplyTo, is_( top ) )

	# Now "save" the note
	note._p_mtime = 1

	ext['inReplyTo'] = ReferenceObject()
	ext['references'] = [ReferenceObject()]
	# and it doesn't change
	update_from_external_object( note, ext )

	assert_that( note.inReplyTo, is_( top ) )
	assert_that( note.references, has_length( 0 ) )
