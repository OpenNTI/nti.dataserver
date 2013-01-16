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

class _Mutable_P_Mtime_Note(_Note):
	_p_mtime = None

def Note():
	n = _Mutable_P_Mtime_Note()
	n.applicableRange = ContentRangeDescription()
	return n

@interface.implementer(nti_interfaces.IWeakRef)
class ReferenceObject(object):

	external_ntiid_oid = 'abc'

	ref_is_deleted = False
	_entity_id = 1 # Match intid_wref

	def __call__(self):
		if not self.ref_is_deleted:
			return self

	def to_external_ntiid_oid( self ):
		return self.external_ntiid_oid

def test_write_external_reply_to():
	top = ReferenceObject()
	note = Note()
	note.inReplyTo = top

	ext = note.toExternalObject()

	assert_that( ext, has_entry( 'inReplyTo', ReferenceObject.external_ntiid_oid ) )
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
	ext = note.toExternalObject()

	assert_that( ext, has_entry( 'inReplyTo', 'tag:nextthought.com,2011-10:Missing-x' ) )
	assert_that( ext, has_entry( 'references', ['tag:nextthought.com,2011-10:Missing-y'] ) )


def test_update_external_reply_to():
	top = ReferenceObject()
	note = Note()

	ext = note.toExternalObject()
	ext['applicableRange'] = ContentRangeDescription()

	ext['inReplyTo'] = top
	top.sharingTargets = () # required by note's first update
	top.creator = None
	note.updateFromExternalObject( ext )

	assert_that( note.inReplyTo, is_( top ) )

	# Now "save" the note
	note._p_mtime = 1

	ext['inReplyTo'] = ReferenceObject()
	ext['references'] = [ReferenceObject()]
	# and it doesn't change
	note.updateFromExternalObject( ext )

	assert_that( note.inReplyTo, is_( top ) )
	assert_that( note.references, has_length( 0 ) )
