#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_item
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import contains
from hamcrest import is_
from hamcrest import is_not as does_not

import nti.tests
from nti.tests import is_true, is_false

from zope.component import eventtesting

def setUpModule():
	nti.tests.module_setup( set_up_packages=('nti.dataserver',) )
	eventtesting.setUp()

def tearDownModule():
	nti.tests.module_teardown()
	eventtesting.clearEvents()

#from zope import interface
#from nti.dataserver import interfaces as nti_interfaces
#from nti.dataserver.users import interfaces

from nti.dataserver.users import FriendsList
from nti.dataserver.users import User

import nti.externalization.internalization
import nti.externalization.externalization
from nti.externalization.externalization import to_external_object
from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.internalization import update_from_external_object

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDS, WithMockDSTrans
from nti.dataserver.users import users
from nti.dataserver.contenttypes import Note
from nti.contentrange.contentrange import ContentRangeDescription

def test_update_friends_list_name():
	class O(object):
		username = 'foo'
		_avatarURL = 'BAD'

	o = FriendsList('MyList')
	ext_value = nti.externalization.externalization.to_external_object( o )
	assert_that( ext_value, has_entry( 'Username', 'MyList' ) )
	assert_that( ext_value, has_entry( 'alias', 'MyList' ) )
	assert_that( ext_value, has_entry( 'realname', 'MyList' ) )

	nti.externalization.internalization.update_from_external_object( o, {'realname': "My Funny Name"} )

	ext_value = nti.externalization.externalization.to_external_object( o )

	assert_that( ext_value, has_entry( 'Username', 'MyList' ) )
	assert_that( ext_value, has_entry( 'realname', 'My Funny Name' ) )
	assert_that( ext_value, has_entry( 'alias', 'My Funny Name' ) )

@WithMockDSTrans
def test_update_friends_list():
	owner = users.User.create_user( username='owner@bar' )
	user = users.User.create_user( username='1foo@bar' )
	user2 = users.User.create_user( username='2foo2@bar' )
	user3 = users.User.create_user( username='3foo3@bar' )
	user4 = users.User.create_user( username='4foo4@bar' )
	user5 = users.User.create_user( username='5foo5@bar' )
	user6 = users.User.create_user( username='6foo6@bar' )
	user7 = users.User.create_user( username='7foo7@bar' )
	user8 = users.User.create_user( username='8foo8@BAR' )

	fl = FriendsList( 'MyList' )
	fl.creator = owner

	# Cannot add self
	fl.updateFromExternalObject( {'friends': [owner] } )
	assert_that( list(fl), has_length( 0 ) )

	# Can add a few to empty
	fl.updateFromExternalObject( {'friends': [user, user2] } )
	assert_that( list(fl), has_length( 2 ) )
	assert_that( sorted(fl), contains( user, user2 ) )

	# Can add one more
	fl.updateFromExternalObject( {'friends': [user, user2, user3, user, user2, user3] } )
	assert_that( list(fl), has_length( 3 ) )
	assert_that( sorted(fl), contains( user, user2, user3 ) )

	# Can go back to one
	fl.updateFromExternalObject( {'friends': [user2] } )
	assert_that( list(fl), has_length( 1 ) )
	assert_that( list(fl), contains( user2 ) )

	fl.updateFromExternalObject( {'friends': [user] } )
	assert_that( list(fl), contains( user ) )

	fl.updateFromExternalObject( {'friends': [user, user2, user3, user, user2, user3] } )
	assert_that( list(fl), has_length( 3 ) )
	assert_that( sorted(fl), contains( user, user2, user3 ) )

	updated = fl.updateFromExternalObject( {'friends': [user.username, user2.username, user3.username, user4.username]} )
	assert_that( updated, is_true() )
	assert_that( list(fl), has_length( 4 ) )
	assert_that( sorted(fl), contains( user, user2, user3, user4 ) )

	updated = fl.updateFromExternalObject( {'friends': [user4.username, user3.username, user2.username, user.username]} )
	assert_that( updated, is_false() ) # no change

	updated = fl.updateFromExternalObject( {'friends': [user.username, user2.username, user3.username, user4.username,
														user5.username, user6.username]} )
	assert_that( updated, is_true() )
	assert_that( list(fl), has_length( 6 ) )
	assert_that( sorted(fl), contains( user, user2, user3, user4, user5, user6 ) )


	updated = fl.updateFromExternalObject( {'friends': [user.username, user2.username, user3.username, user4.username,
														user5.username, user6.username, user7.username, user8.username]} )
	assert_that( updated, is_true() )
	assert_that( list(fl), has_length( 8 ) )
	assert_that( sorted(fl), contains( user, user2, user3, user4, user5, user6, user7, user8 ) )

	# Break some refs
	users.User.delete_user( user.username )

	updated = fl.updateFromExternalObject( {'friends': [user.username, user2.username, user3.username, user4.username,
														user5.username, user6.username, user7.username, user8.username]} )
	assert_that( updated, is_true() )
	assert_that( list(fl), has_length( 7 ) )
	assert_that( sorted(fl), contains( user2, user3, user4, user5, user6, user7, user8 ) )

@WithMockDSTrans
def test_create_update_dynamic_friendslist():
	ds = mock_dataserver.current_mock_ds
	user1 = User.create_user( ds, username='foo23' )
	user2 = User.create_user( ds, username='foo12' )
	user3 = User.create_user( ds, username='foo13' )

	fl1 = users.DynamicFriendsList(username='Friends')
	fl1.creator = user1 # Creator must be set

	user1.addContainedObject( fl1 )
	fl1.addFriend( user2 )

	assert_that( user2.dynamic_memberships, has_item( fl1 ) )

	fl1.updateFromExternalObject( {'friends': [user3.username]} )

	assert_that( user3.dynamic_memberships, has_item( fl1 ) )
	assert_that( to_external_object( user3 ), has_entry( 'Communities', has_item( has_entry( 'realname', 'Friends' ) ) ) )
	assert_that( user2.dynamic_memberships, does_not( has_item( fl1 ) ) )


@WithMockDSTrans
def test_delete_dynamic_friendslist_clears_memberships():
	ds = mock_dataserver.current_mock_ds
	user1 = User.create_user( ds, username='foo23' )
	user2 = User.create_user( ds, username='foo12' )

	fl1 = users.DynamicFriendsList(username='Friends')
	fl1.creator = user1 # Creator must be set

	user1.addContainedObject( fl1 )
	fl1.addFriend( user2 )

	assert_that( list(user2.dynamic_memberships), has_item( fl1 ) )
	assert_that( list(user2.entities_followed), has_item( fl1 ) )

	eventtesting.clearEvents()
	assert_that( user1.deleteContainedObject( fl1.containerId, fl1.id ), is_( fl1 ) )

	# If the events don't fire correctly, the weakref will still have this cached
	# so it will still seem to be present
	assert_that( list(user2.dynamic_memberships), does_not( has_item( fl1 ) ) )
	assert_that( list(user2.entities_followed), does_not( has_item( fl1 ) ) )
	assert_that( user2, has_property( '_dynamic_memberships', has_length( 1 ) ) )



from nti.dataserver.tests.test_authorization_acl import permits
from nti.dataserver import authorization as nauth

@WithMockDS(with_changes=True)
def test_sharing_with_dfl():
	ds = mock_dataserver.current_mock_ds
	with mock_dataserver.mock_db_trans( ds ):
		# Set up listeners
		ds.add_change_listener( users.onChange )

		# Create a user with a DFL and two friends in the DFL
		parent_user = users.User.create_user( username="foo@bar" )
		parent_dfl = users.DynamicFriendsList( username="ParentFriendsList" )
		parent_dfl.creator = parent_user
		parent_user.addContainedObject( parent_dfl )

		child_user = users.User.create_user( username="baz@bar" )
		parent_dfl.addFriend( child_user )

		other_user = users.User.create_user( username="other@bar" )
		parent_dfl.addFriend( other_user )

		# Reset notification counts (Circled notices would have gone out)
		for u in (parent_user, child_user, other_user):
			u.notificationCount.value = 0

		with parent_user.updates():
			# Create a note
			parent_note = Note()
			parent_note.applicableRange = ContentRangeDescription()
			parent_note.creator = parent_user
			parent_note.body = ['Hi there']
			parent_note.containerId = 'tag:nti'

			# (Check base states)
			for u in (child_user, other_user):
				child_stream = u.getContainedStream( parent_note.containerId )
				assert_that( child_stream, has_length( 0 ) )

			# Share the note with the DFL and thus its two members
			parent_note.addSharingTarget( parent_dfl )
			parent_user.addContainedObject( parent_note )

		# Sharing with the DFL caused broadcast events and notices to go out
		# to the members of the DFL. These members have the shared object
		# in their stream
		for u in (child_user, other_user):
			__traceback_info__ = u
			child_stream = u.getContainedStream( parent_note.containerId )
			assert_that( child_stream, has_length( 1 ) )
			assert_that( u.notificationCount, has_property( 'value', 1 ) )


		# If a member of the DFL replies to the note,
		# then the same thing happens,
		with child_user.updates():
			child_note = Note()
			child_note.creator = child_user
			child_note.body = ['A reply']
			child_note.containerId = 'tag:nti'
			child_note.applicableRange = ContentRangeDescription()

			ext_obj = to_external_object( child_note )
			ext_obj['inReplyTo'] = to_external_ntiid_oid( parent_note )

			update_from_external_object( child_note, ext_obj, context=ds )

			assert_that( child_note, has_property( 'inReplyTo', parent_note ) )
			assert_that( child_note, has_property( 'sharingTargets', set((parent_dfl,parent_user)) ) )

			child_user.addContainedObject( child_note )

		other_stream = other_user.getContainedStream( child_note.containerId )
		assert_that( other_stream, has_length( 2 ) )
		assert_that( other_user.notificationCount, has_property( 'value', 2 ) )
		#parent_stream = parent_user.getContainedStream( parent_note.containerId )
		#assert_that( parent_stream, has_length( 1 ) )


		# If a member of the DFL shares something unrelated with the group,
		# it is visible to the creator in the shared data, in the stream, and
		# in the notification count
		parent_user.notificationCount.value = 0
		with child_user.updates():
			child_note = Note()
			child_note.creator = child_user
			child_note.body = ['From the child']
			child_note.containerId = 'tag:nti2'
			child_note.applicableRange = ContentRangeDescription()
			child_note.addSharingTarget( parent_dfl )

			assert_that( child_note, has_property( 'sharingTargets', set((parent_dfl,)) ) )

			child_user.addContainedObject( child_note )

		# The shared note is in the shared data for the owner of the DFL
		parent_shared_cont = parent_user.getSharedContainer( child_note.containerId )
		assert_that( parent_shared_cont, has_length( 1 ) )
		assert_that( parent_shared_cont, contains( child_note ) )
		# And in the stream of the owner of the DFL
		parent_stream = parent_user.getContainedStream( child_note.containerId )
		assert_that( parent_stream, has_length( 1 ) )
		# and as a notification for the DFL owner
		assert_that( parent_user.notificationCount, has_property( 'value', 1 ) )

		# and is in the other member's stream as well
		other_stream = other_user.getContainedStream( child_note.containerId )
		assert_that( other_stream, has_length( 1 ) )
		assert_that( other_user.notificationCount, has_property( 'value', 3 ) )

		# This Note provides ACL access to its creator and the members of the DFL
		# (TODO: This is implemented by expanding the membership list of the DFL
		# when the ACL is constructed. The other option is to have the DFL
		# appear in the principal list of the user, as is done for communities; that
		# would change this test.)
		assert_that( child_note, permits( child_user, nauth.ACT_READ ) )
		assert_that( child_note, permits( parent_user, nauth.ACT_READ ) )
		assert_that( child_note, permits( other_user, nauth.ACT_READ ) )
