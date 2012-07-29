#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, has_property
from hamcrest import same_instance
from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_item
does_not = is_not
from hamcrest import none

from nti.dataserver.generations.install import evolve as real_install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve17 import evolve

from nti.dataserver import containers, datastructures
from nti.dataserver.contenttypes import Note
from nti.externalization.persistence import PersistentExternalizableList, PersistentExternalizableWeakList
from nti.dataserver.activitystream_change import Change


import nti.tests
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS
from nti.dataserver.chat_transcripts import _MeetingTranscriptStorage as MTS
from BTrees.OOBTree import OOBTree

import fudge

from nti.deprecated import hides_warnings

import zope.intid
import zc.intid
from zope import component

class TestEvolve17(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve17(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			dataserver_folder = real_install( context )
			# Before we put in any other objects, drop the intid utility
			# (Both the one we just installed and the one that already exists
			# in our mock transaction)
			for lsm in (component.getSiteManager(),dataserver_folder.getSiteManager()):
				lsm.unregisterUtility( provided=zope.intid.IIntIds )
				lsm.unregisterUtility( provided=zc.intid.IIntIds )

			ExampleDatabaseInitializer().install( context )


			jason = dataserver_folder['users']['jason.madden@nextthought.com']
			# Give me some data to migrate over
			note = Note()
			note.containerId = "foo:bar"
			assert_that( note, does_not( has_property( '_ds_intid' ) ) )
			jason.addContainedObject( note )
			note_id = note.id
			assert_that( note, does_not( has_property( '_ds_intid' ) ) )

			mts = MTS(note)
			mts.containerId = 'foo:bar'
			jason.addContainedObject( note )
			mts_id = mts.id

			# Make his sharing structures match the old ones

			# For things that are shared explicitly with me, we maintain a structure
			# that parallels the contained items map. The first level is
			# from container ID to a list of weak references to shared objects.
			# (Un-sharing something, which requires removal from an arbitrary
			# position in the list, should be rare.) Notice that we must NOT
			# have the shared storage set or use IDs, because these objects
			# are not owned by us.

			jason.containersOfShared = datastructures.ContainedStorage( weak=True,
																	   create=False,
																	   containerType=containers.EventlessLastModifiedBTreeContainer,
																	   set_ids=False )

			# For muted conversations, which can be unmuted, there is an
			# identical structure. References are moved in and out of this
			# container as conversations are un/muted. The goal of this structure
			# is to keep reads fast. Only writes--changing the muted status--are slow
			jason.containers_of_muted = datastructures.ContainedStorage( weak=True,
																	   create=False,
																	   containerType=containers.EventlessLastModifiedBTreeContainer,
																	   set_ids=False )

			# A cache of recent items that make of the stream. Going back
			# further than this requires walking through the containersOfShared.
			# Map from containerId -> PersistentExternalizableWeakList
			# TODO: Rethink this. It's terribly inefficient.
			jason.streamCache = OOBTree()

			note_to_share = Note()
			note_to_share.containerId = 'shared'
			ken = dataserver_folder['users']['ken.parker@nextthought.com']
			ken.addContainedObject( note_to_share )
			shared_note_id = note_to_share.id

			jason.containersOfShared.addContainedObject( note_to_share )
			jason.containers_of_muted.addContainedObject( note_to_share )
			jason.streamCache[note_to_share.containerId] = PersistentExternalizableWeakList()
			jason.streamCache[note_to_share.containerId].append( Change( Change.SHARED, note_to_share ) )


		# Evolve
		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			intids = ds_folder.getSiteManager().getUtility( zc.intid.IIntIds )
			jason = ds_folder['users']['jason.madden@nextthought.com']
			# intids were applied to users...
			assert_that( intids.getObject( intids.getId( jason ) ), is_( same_instance( jason ) ) )
			# ...their friends lists
			assert_that( intids.getObject( intids.getId( jason.friendsLists['Everyone']  ) ), is_( same_instance( jason.friendsLists['Everyone']  ) ) )

			# ...and their owned data
			note = jason.getContainedObject( 'foo:bar', note_id )
			assert_that( intids.getObject( intids.getId( note ) ), is_( same_instance( note ) ) )

			# ...and bad data vanished
			assert_that( jason.getContainedObject( 'foo:bar', mts_id ), is_( none() ) )

			# ...and that the stream works
			assert_that( jason.getContainedStream( 'shared' )[0], is_( Change ) )

			# ...as do shared objects
			assert_that( jason.getSharedContainer( 'shared' ), has_item( has_property( 'id', shared_note_id ) ) )
