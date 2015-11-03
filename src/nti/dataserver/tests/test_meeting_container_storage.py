#!/usr/bin/env python2.7


from hamcrest import (assert_that, is_,
					  has_key,  not_none,
					    none, has_property, has_entry,
					  has_item, has_items)
from hamcrest import is_not
does_not = is_not
import unittest
from zope import (interface, component)

try:
	import cPickle as pickle
except ImportError:
	import pickle

#import nti.chatserver.chat as chat
from nti.chatserver import interfaces as chat_interfaces

import nti.dataserver.users as users
from nti.ntiids import ntiids
import nti.dataserver.meeting_container_storage as mcs
from zope.annotation import interfaces as ant_interfaces

from mock_dataserver import WithMockDS
from . import mock_dataserver


class TestMeetingContainer(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

	occupant_names = ()
	ID_FL1 = ntiids.make_ntiid( provider='foo@bar', nttype=ntiids.TYPE_MEETINGROOM_GROUP, specific='fl1' )

	@WithMockDS
	def test_no_entity( self ):
		ds = self.ds
		mc = mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			assert_that( mc.get( self.ID_FL1 ), is_( none() ) )
			assert_that( mc.get( None ), is_( none() ) )

	@WithMockDS
	def test_entity_no_list( self ):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			users.User.create_user( ds, username='foo@bar', password='temp001' )

		mc = mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			assert_that( ds.root['users'], has_key( 'foo@bar' ) )
			assert_that( mc.get( self.ID_FL1 ), is_( none() ) )
			assert_that( mc.get( None ), is_( none() ) )

	@WithMockDS
	def test_entity_with_list( self ):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = users.User.create_user( ds, username='foo@bar', password='temp001' )
			ds.root['users']['foo@bar'] = user
			ds.root['users']['friend@bar'] = users.User.create_user( ds, username='friend@bar', password='temp001' )
			fl1 = user.maybeCreateContainedObjectWithType(  'FriendsLists', { 'Username': 'fl1', 'friends': ['friend@bar'] } )
			fl1.containerId = 'FriendsLists'
			user.addContainedObject( fl1 )
			assert_that( fl1, is_( not_none() ) )
			assert_that( user.getContainedObject( 'FriendsLists', 'fl1' ), is_( fl1 ) )


		mc = mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			assert_that( ds.root['users'], has_key( 'foo@bar' ) )

			adapt = mc.get( self.ID_FL1 )
			assert_that( adapt, is_( not_none() ) )
			assert_that( interface.providedBy( adapt ), has_item( chat_interfaces.IMeetingContainer ) )


class MockMeeting(object):
	Active = True
	occupant_names = ()


class TestFriendsListAdaptor( unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

	occupant_names = ()
	@WithMockDS
	def test_create_and_empty( self ):
		ds = self.ds
		mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			user = users.User.create_user( ds, username='foo@bar', password='temp001' )
			ds.root['users']['foo@bar'] = user
			ds.root['users']['friend@bar'] = users.User.create_user( ds, username='friend@bar', password='temp001' )
			fl1 = user.maybeCreateContainedObjectWithType(  'FriendsLists', { 'Username': 'fl1', 'friends': ['friend@bar'] } )
			fl1.containerId = 'FriendsLists'
			fl1.creator = user
			fl1.addFriend( ds.root['users']['friend@bar'] )
			user.addContainedObject( fl1 )

		self.Active = True
		def c(): return self

		with mock_dataserver.mock_db_trans(ds):
			adapt = component.queryAdapter( fl1, chat_interfaces.IMeetingContainer )

			# Missing occupants fails
			assert_that( adapt.create_meeting_from_dict( None, {}, c ), is_( none() ) )
			# Bad occupants fails
			assert_that( adapt.create_meeting_from_dict( None, {'Occupants': ['me']}, c ), is_( none() ) )

			# Dict with right occupants and tuple succeeds
			# only the owner can create
			d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'foo@bar' }
			assert_that( adapt.create_meeting_from_dict( None, d, c ), is_(self) )
			assert_that( d['Occupants'], has_item( 'friend@bar' ) )
			assert_that( d['Occupants'], has_item( ('foo@bar', 1234 ) ) )
			assert_that( ant_interfaces.IAnnotations( fl1 ), has_entry( adapt.ACTIVE_ROOM_ATTR, self ) )


			# And again fails because room is still active.
			d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'friend@bar' }
			assert_that( adapt.create_meeting_from_dict( None, d, c ), is_( none() ) )

			adapt.meeting_became_empty( None, self )
			assert_that( ant_interfaces.IAnnotations( fl1 ), does_not( has_key( adapt.ACTIVE_ROOM_ATTR ) ) )


	@WithMockDS
	def test_enter_active( self ):
		ds = self.ds
		mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			user = users.User.create_user( ds, username='foo@bar', password='temp001' )
			ds.root['users']['foo@bar'] = user
			ds.root['users']['friend@bar'] = users.User.create_user( ds, username='friend@bar', password='temp001' )
			fl1 = user.maybeCreateContainedObjectWithType(  'FriendsLists', { 'Username': 'fl1', 'friends': ['friend@bar'] } )
			fl1.containerId = 'FriendsLists'
			fl1.creator = user
			fl1.addFriend( ds.root['users']['friend@bar'] )
			user.addContainedObject( fl1 )

		c = MockMeeting

		with mock_dataserver.mock_db_trans(ds):
			adapt = component.queryAdapter( fl1, chat_interfaces.IMeetingContainer )

			# No active meeting fails.
			assert_that( adapt.enter_active_meeting( None, {} ), is_( none() ) )

			# Create active meeting. Only the owner can create
			d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'foo@bar' }
			room = adapt.create_meeting_from_dict( None, d, c )
			assert_that( room, is_(MockMeeting) )
			# The results have an acl
			assert_that( room, has_property( '__acl__' ) )
			# The results can be pickled
			# ...once we drop the bad __parent__
			old_p = room.__parent__
			del room.__parent__
			s = pickle.dumps( room, pickle.HIGHEST_PROTOCOL )
			r2 = pickle.loads( s )
			assert_that( r2.__acl__, is_( room.__acl__ ) )
			room.__parent__ = old_p
			# Bad sender fails
			assert_that( adapt.enter_active_meeting( None, {'Creator': 'me'} ), is_( none() ) )

			# Valid sender works
			## A friend  reenters an existing room
			assert_that( adapt.enter_active_meeting( None, {'Creator': 'friend@bar'} ), is_( MockMeeting ) )
			## The creator gets a fresh one
			assert_that( adapt.enter_active_meeting( None, {'Creator': user.username} ), is_( none() ) )
