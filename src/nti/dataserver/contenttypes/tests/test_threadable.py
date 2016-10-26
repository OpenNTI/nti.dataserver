#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import interface
from nti.dataserver import interfaces as nti_interfaces

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import contains_inanyorder

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.testing.matchers import validly_provides

from nti.containers.containers import CaseInsensitiveLastModifiedBTreeContainer

from nti.dataserver.contenttypes import Note as _Note
from nti.contentrange.contentrange import ContentRangeDescription
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


class _Mutable_P_Mtime_Note(_Note):
	_p_mtime = None

def Note():
	n = _Mutable_P_Mtime_Note()
	n.applicableRange = ContentRangeDescription()
	return n

from nti.intid.wref import WeakRef

@interface.implementer(nti_interfaces.IThreadable)
class ReferenceObject(WeakRef):
	# Extend the real ref, to get its implementation,
	# but override the moving parts

	__slots__ = ('external_ntiid_oid', 'ref_is_deleted', 'creator', 'sharingTargets', 'references', 'inReplyTo', 'replies', 'referents')

	def __init__( self ):
		# deliberately not calling super
		self._entity_id = 1
		self.external_ntiid_oid = 'abc'
		self.ref_is_deleted = False
		self.references = ()
		self.inReplyTo = None
		self.replies = ()
		self.referents = ()

	def __call__(self):
		if not self.ref_is_deleted:
			return self

	def to_external_ntiid_oid( self ):
		return self.external_ntiid_oid

class TestThreadable(DataserverLayerTest):
	def test_write_external_reply_to(self):
		top = ReferenceObject()
		note = Note()
		note.inReplyTo = top

		ext = to_external_object( note )

		assert_that( ext, has_entry( 'inReplyTo', 'abc' ) )
		assert_that( ext, has_entry( 'references', [] ) )

	def test_write_external_reply_to_deleted(self):
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


		assert_that( note, validly_provides( nti_interfaces.IInspectableWeakThreadable) )

	def test_update_external_reply_to(self):
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

	@WithMockDSTrans
	def test_adding_and_removing_maintains_reply_chains(self):
		#self.ds = mock_dataserver.current_mock_ds
		container = CaseInsensitiveLastModifiedBTreeContainer()
		self.ds.dataserver_folder['container'] = container

		root = Note()
		container['root'] = root

		direct_reply = Note()
		direct_reply.inReplyTo = root
		container['child'] = direct_reply

		assert_that( list(root.replies), is_( [direct_reply] ) )
		assert_that( list(root.referents), is_( [direct_reply] ) )

		direct_reply_child = Note()
		direct_reply_child.inReplyTo = direct_reply
		container['grandchild1'] = direct_reply_child

		assert_that( list(direct_reply.replies), is_( [direct_reply_child] ) )
		assert_that( list(direct_reply.referents), is_( [direct_reply_child] ) )

		assert_that( list(root.replies), is_( [direct_reply] ) )
		assert_that( list(root.referents), contains_inanyorder( direct_reply, direct_reply_child ) )

		grandchild2 = Note()
		grandchild2.inReplyTo = direct_reply
		container['grandchild2'] = grandchild2

		assert_that( list(direct_reply.replies), contains_inanyorder( direct_reply_child, grandchild2 ) )
		assert_that( list(direct_reply.referents), contains_inanyorder( direct_reply_child, grandchild2 ) )

		assert_that( list(root.replies), is_( [direct_reply] ) )
		assert_that( list(root.referents), contains_inanyorder( direct_reply, direct_reply_child, grandchild2 ) )
		
		del container['grandchild1']

		assert_that( list(direct_reply.replies), is_( [grandchild2] ) )
		assert_that( list(direct_reply.referents), is_( [grandchild2] ) )

		assert_that( list(root.replies), is_( [direct_reply] ) )
		assert_that( list(root.referents), contains_inanyorder( direct_reply, grandchild2 ) )

		del container['child']

		assert_that( list(root.replies), is_( [] ) )
		assert_that( list(root.referents), is_( [grandchild2] ) )
		
	@WithMockDSTrans
	def test_most_recent_replies(self):

		container = CaseInsensitiveLastModifiedBTreeContainer()
		self.ds.dataserver_folder['container'] = container
		
		root = Note()
		container['root'] = root
		
		assert_that(root.most_recent_reply, is_(None))

		first_reply = Note()
		first_reply.inReplyTo = root
		container['first_reply'] = first_reply
		
		assert_that(root.most_recent_reply, is_(first_reply))
		
		second_reply = Note()
		second_reply.inReplyTo = root
		container['second_reply'] = second_reply
			
		assert_that(root.most_recent_reply, is_(second_reply))
		
		grandchild_reply = Note()
		grandchild_reply.inReplyTo = first_reply
		container['grandchild_reply'] = grandchild_reply
		
		assert_that(root.most_recent_reply, is_(second_reply))
			