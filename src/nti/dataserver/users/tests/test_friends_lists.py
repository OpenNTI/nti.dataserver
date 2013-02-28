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

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_item
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import contains
from hamcrest import is_
from hamcrest import same_instance
from hamcrest import is_in
from hamcrest import is_not as does_not
is_not = does_not
from hamcrest import greater_than_or_equal_to
import nti.tests
from nti.tests import is_true, is_false

from zope.component import eventtesting

def setUpModule():
	nti.tests.module_setup( set_up_packages=('nti.dataserver',) )

def tearDownModule():
	nti.tests.module_teardown()

#from zope import interface
#from nti.dataserver import interfaces as nti_interfaces
#from nti.dataserver.users import interfaces

from nti.dataserver.users import DynamicFriendsList
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
	ntiid = o.NTIID
	ext_value = nti.externalization.externalization.to_external_object( o )
	assert_that( ext_value, has_entry( 'Username', 'MyList' ) )
	assert_that( ext_value, has_entry( 'alias', 'MyList' ) )
	assert_that( ext_value, has_entry( 'realname', 'MyList' ) )

	nti.externalization.internalization.update_from_external_object( o, {'realname': "My Funny Name"} )

	ext_value = nti.externalization.externalization.to_external_object( o )

	assert_that( ext_value, has_entry( 'Username', 'MyList' ) )
	assert_that( ext_value, has_entry( 'realname', 'My Funny Name' ) )
	assert_that( ext_value, has_entry( 'alias', 'My Funny Name' ) )

	# NTIID didn't change
	assert_that( o.NTIID, is_( ntiid ) )
	# in fact its cached
	assert_that( o.NTIID, is_( same_instance( ntiid ) ) )

	# Username changing changes it though
	o.creator = O()
	assert_that( o.NTIID, is_not( ntiid ) )

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

@WithMockDS
def test_create_update_dynamic_friendslist():
	ds = mock_dataserver.current_mock_ds
	with mock_dataserver.mock_db_trans( ds ):
		user1 = User.create_user( ds, username='foo23' )
		user2 = User.create_user( ds, username='foo12' )
		user3 = User.create_user( ds, username='foo13' )

		fl1 = users.DynamicFriendsList(username='Friends')
		fl1.creator = user1 # Creator must be set

		user1.addContainedObject( fl1 )
		fl1.addFriend( user2 )

		assert_that( user2.dynamic_memberships, has_item( fl1 ) )
		assert_that( user2.entities_followed, has_item( fl1 ) )

	for u in user1, user2, user3:
		u._p_deactivate()
		u._p_invalidate()
		assert_that( u, has_property( '__dict__', {} ) )

	with mock_dataserver.mock_db_trans( ds ):
		# This process actually activates the objects directly, immediately, during the
		# iteration process
		fl1.updateFromExternalObject( {'friends': [user3.username]} )

		assert_that( user3.dynamic_memberships, has_item( fl1 ) )
		assert_that( to_external_object( user3 ), has_entry( 'Communities', has_item( has_entry( 'realname', 'Friends' ) ) ) )

		assert_that( user2.dynamic_memberships, does_not( has_item( fl1 ) ) )
		assert_that( user2.entities_followed, does_not( has_item( fl1 ) ) )
		assert_that( to_external_object( user2 ), has_entry( 'Communities', does_not( has_item( has_entry( 'realname', 'Friends' ) ) ) ) )

		# The external form masquerades as a normal FL...
		x = to_external_object( fl1 )
		assert_that( x, has_entry( 'Class', 'FriendsList' ) )
		assert_that( x, has_entry( 'MimeType', 'application/vnd.nextthought.friendslist' ) )
		assert_that( x, has_entry( 'NTIID', 'tag:nextthought.com,2011-10:foo23-MeetingRoom:Group-friends' ) )
		# ... with one exception
		assert_that( x, has_entry( 'IsDynamicSharing', True ) )


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

def _note_from( creator, text='Hi there', containerId='tag:nti' ):
	owner_note = Note()
	owner_note.applicableRange = ContentRangeDescription()
	owner_note.creator = creator
	owner_note.body = [text]
	owner_note.containerId = containerId
	return owner_note

def _dfl_sharing_fixture( ds, owner_username='OwnerUser@bar', passwords=None ):
	"""
	Create a user owning a DFL. Two other users are added to the dfl.

	:return: A tuple (owner, member1, member2, dfl)
	"""
	ds.add_change_listener( users.onChange )
	password_kwargs = {}
	if passwords:
		password_kwargs = {'password': passwords}
	# Create a user with a DFL and two friends in the DFL
	owner_user = users.User.create_user( username=owner_username, **password_kwargs )
	parent_dfl = users.DynamicFriendsList( username="ParentFriendsList" )
	parent_dfl.creator = owner_user
	owner_user.addContainedObject( parent_dfl )

	member_user = users.User.create_user( username="memberuser@bar", **password_kwargs )
	parent_dfl.addFriend( member_user )

	member_user2 = users.User.create_user( username="memberuser2@bar", **password_kwargs )
	parent_dfl.addFriend( member_user2 )

	# Reset notification counts (Circled notices would have gone out)
	for u in (owner_user, member_user, member_user2):
		u.notificationCount.value = 0

	return owner_user, member_user, member_user2, parent_dfl

def _assert_that_item_is_in_contained_stream_and_data_with_notification_count( user, item, count=1 ):
	__traceback_info__ = user, item
	child_stream = user.getContainedStream( item.containerId )
	assert_that( child_stream, has_length( count ) )
	assert_that( child_stream, has_item( has_property( 'object', item ) ), "stream has right item" )
	assert_that( user.notificationCount, has_property( 'value', count ), "notification count has right size" )

	shared_data = user.getSharedContainer( item.containerId )
	assert_that( shared_data, has_item( item ), "item is in shared data" )
	assert_that( shared_data, has_length( greater_than_or_equal_to( count ) ), "shared data has right size" )

@WithMockDS(with_changes=True)
def test_sharing_with_dfl():
	ds = mock_dataserver.current_mock_ds
	with mock_dataserver.mock_db_trans( ds ):
		owner_user, member_user, member_user2, parent_dfl = _dfl_sharing_fixture( ds )

		with owner_user.updates():
			# Create a note
			owner_note = _note_from( owner_user )

			# (Check base states)
			for u in (member_user, member_user2):
				child_stream = u.getContainedStream( owner_note.containerId )
				assert_that( child_stream, has_length( 0 ) )

			# Share the note with the DFL and thus its two members
			owner_note.addSharingTarget( parent_dfl )
			owner_user.addContainedObject( owner_note )

		# Sharing with the DFL caused broadcast events and notices to go out
		# to the members of the DFL. These members have the shared object
		# in their stream and shared data
		for u in (member_user, member_user2):
			_assert_that_item_is_in_contained_stream_and_data_with_notification_count( u, owner_note )



		# If a member of the DFL replies to the note,
		# then the same thing happens,
		with member_user.updates():
			child_note = _note_from( member_user, 'A reply' )

			ext_obj = to_external_object( child_note )
			ext_obj['inReplyTo'] = to_external_ntiid_oid( owner_note )

			update_from_external_object( child_note, ext_obj, context=ds )

			assert_that( child_note, has_property( 'inReplyTo', owner_note ) )
			assert_that( child_note, has_property( 'sharingTargets', set((parent_dfl,owner_user)) ) )

			member_user.addContainedObject( child_note )

		# Notices go out to the other members of the DFL, including the owner
		_assert_that_item_is_in_contained_stream_and_data_with_notification_count( member_user2, child_note, 2 )
		_assert_that_item_is_in_contained_stream_and_data_with_notification_count( owner_user, child_note, 1 )


@WithMockDS(with_changes=True)
def test_sharing_with_dfl_member_shares_top_level():
	"""
	If a member of the DFL shares something unrelated with the DFL,
	it is visible to the creator of the DFL in the shared data, in the stream, and
	in the notification count. It is also in the 'iterntiids' value for all
	people.
	"""

	ds = mock_dataserver.current_mock_ds
	with mock_dataserver.mock_db_trans( ds ):
		owner_user, member_user, member_user2, parent_dfl = _dfl_sharing_fixture( ds )

		with member_user.updates():
			child_note = _note_from( member_user, 'From the child' )
			child_note.addSharingTarget( parent_dfl )

			assert_that( child_note, has_property( 'sharingTargets', set((parent_dfl,)) ) )

			member_user.addContainedObject( child_note )

		# The shared note is in the shared data for the owner of the DFL
		# And in the stream of the owner of the DFL
		# and as a notification for the DFL owner
		_assert_that_item_is_in_contained_stream_and_data_with_notification_count( owner_user, child_note, 1 )


		# and is in the other member's stream and shared data as well
		_assert_that_item_is_in_contained_stream_and_data_with_notification_count( member_user2, child_note, 1 )

		# This Note provides ACL access to its creator and the members of the DFL
		# (TODO: This is implemented by expanding the membership list of the DFL
		# when the ACL is constructed. The other option is to have the DFL
		# appear in the principal list of the user, as is done for communities; that
		# would change this test.)
		assert_that( child_note, permits( member_user, nauth.ACT_READ ) )
		assert_that( child_note, permits( owner_user, nauth.ACT_READ ) )
		assert_that( child_note, permits( member_user2, nauth.ACT_READ ) )

		# Even though the other members do not have data in this NTIID, they
		# still register that they are interested in it
		for member in (owner_user, member_user, member_user2):
			ids = list(member.iterntiids())
			__traceback_info__ = member, ids
			assert_that( ids, contains( child_note.containerId ) )

@WithMockDS(with_changes=True)
def test_replace_dfl_sharing_with_a_member():
	"""
	After removing the DFL share from a note and replace it with a direct sharing
	of a DFL member, make sure the note is still accessible
	"""
	ds = mock_dataserver.current_mock_ds
	with mock_dataserver.mock_db_trans(ds):
		ds.add_change_listener( users.onChange )
		jmadden = users.User.create_user( username='jmadden@nextthought.com' )
		sjohnson = users.User.create_user( username='sjohnson@nextthought.com' )

		ntusrs = DynamicFriendsList(username='ntusrs')
		ntusrs.creator = jmadden
		jmadden.addContainedObject( ntusrs )
		ntusrs.addFriend( sjohnson )

		note = Note()
		note.body = [u'Violent Blades']
		note.creator = jmadden.username
		note.containerId = u'c1'

		with jmadden.updates():
			note.addSharingTarget( ntusrs )
			note = jmadden.addContainedObject( note )

		scnt = sjohnson.getSharedContainer(  u'c1' )
		assert_that(note, is_in(scnt))

		with jmadden.updates():
			note = jmadden.getContainedObject(u'c1', note.id)
			note.clearSharingTargets()
			note.addSharingTarget( sjohnson )

		scnt = sjohnson.getSharedContainer(  u'c1' )
		assert_that(note, is_in(scnt))
