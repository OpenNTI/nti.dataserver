#!/usr/bin/env python2.7


from hamcrest import (assert_that, is_,
					  has_key,  not_none,
					    none, has_property, has_entry,
					  has_item, has_items)
import unittest
from zope import (interface, component)

try:
	import cPickle as pickle
except ImportError:
	import pickle

#import nti.chatserver.chat as chat
from nti.chatserver import interfaces as chat_interfaces

import nti.dataserver.users as users
import nti.dataserver.providers as providers
import nti.dataserver.classes as classes
from nti.ntiids import ntiids
import nti.dataserver.meeting_container_storage as mcs


from mock_dataserver import WithMockDS, ConfiguringTestBase
import mock_dataserver


class TestMeetingContainer(ConfiguringTestBase):
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
			ds.root['users']['friend@bar'] = users.User( 'friend@bar', 'temp001' )
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


class TestFriendsListAdaptor( ConfiguringTestBase ):
	occupant_names = ()
	@WithMockDS
	def test_create_and_empty( self ):
		ds = self.ds
		mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			user = users.User.create_user( ds, username='foo@bar', password='temp001' )
			ds.root['users']['foo@bar'] = user
			ds.root['users']['friend@bar'] = users.User( 'friend@bar', 'temp001' )
			fl1 = user.maybeCreateContainedObjectWithType(  'FriendsLists', { 'Username': 'fl1', 'friends': ['friend@bar'] } )
			fl1.containerId = 'FriendsLists'
			fl1.creator = user
			fl1.addFriend( ds.root['users']['friend@bar'] )
			user.addContainedObject( fl1 )

		self.Active = True
		def c(): return self
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
		assert_that( getattr( fl1, adapt.ACTIVE_ROOM_ATTR ), is_( self ) )

		# And again fails because room is still active.
		d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'friend@bar' }
		assert_that( adapt.create_meeting_from_dict( None, d, c ), is_( none() ) )

		adapt.meeting_became_empty( None, self )
		assert_that( getattr( fl1, adapt.ACTIVE_ROOM_ATTR, 42 ), is_( 42 ) )

	@WithMockDS
	def test_enter_active( self ):
		ds = self.ds
		mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			user = users.User( 'foo@bar', 'temp001' )
			ds.root['users']['foo@bar'] = user
			ds.root['users']['friend@bar'] = users.User( 'friend@bar', 'temp001' )
			fl1 = user.maybeCreateContainedObjectWithType(  'FriendsLists', { 'Username': 'fl1', 'friends': ['friend@bar'] } )
			fl1.containerId = 'FriendsLists'
			fl1.creator = user
			fl1.addFriend( ds.root['users']['friend@bar'] )
			user.addContainedObject( fl1 )

		c = MockMeeting
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



class TestClassSectionAdapter( ConfiguringTestBase ):
	occupant_names = ()
	@WithMockDS
	def test_create_and_empty( self ):
		ds = self.ds
		mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			user = providers.Provider( 'OU' )
			ds.root['providers']['OU'] = user
			fl1 = user.maybeCreateContainedObjectWithType(  'Classes', None )
			fl1.containerId = 'Classes'
			fl1.ID = 'CS2051'
			fl1.Description = 'CS Class'
			user.addContainedObject( fl1 )

			section = classes.SectionInfo()
			section.ID = 'CS2051.101'
			fl1.add_section( section )
			section.InstructorInfo = classes.InstructorInfo()
			section.enroll( 'chris' )
			section.InstructorInfo.Instructors.append( 'sjohnson' )
			section.Provider = 'OU'


			fl1 = fl1.Sections[0]

		self.Active = True
		def c(): return self
		adapt = component.queryAdapter( fl1, chat_interfaces.IMeetingContainer )
		assert_that( adapt, is_( not_none() ) )
		# Missing occupants fails
		assert_that( adapt.create_meeting_from_dict( None, {}, c ), is_( none() ) )
		# Bad occupants fails
		assert_that( adapt.create_meeting_from_dict( None, {'Creator': 'chris'}, c ), is_( none() ) )

		# Dict with right occupants and tuple succeeds
		# creator is just occupant, not owner
		d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'sjohnson' }
		assert_that( adapt.create_meeting_from_dict( None, d, c ), is_(self) )
		assert_that( d['Occupants'], has_items( 'chris', 'sjohnson' ) )
		assert_that( getattr( fl1, adapt.ACTIVE_ROOM_ATTR ), is_( self ) )

		# And again fails because room is still active.
		d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'sjohnson' }
		assert_that( adapt.create_meeting_from_dict( None, d, c ), is_( none() ) )

		adapt.meeting_became_empty( None, self )
		assert_that( getattr( fl1, adapt.ACTIVE_ROOM_ATTR, 42 ), is_( 42 ) )

	@WithMockDS
	def test_enter_active( self ):
		ds = self.ds
		mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			user = providers.Provider( 'OU' )
			ds.root['providers']['OU'] = user
			fl1 = user.maybeCreateContainedObjectWithType(  'Classes', None )
			fl1.containerId = 'Classes'
			fl1.ID = 'CS2051'
			fl1.Description = 'CS Class'
			user.addContainedObject( fl1 )
			section = classes.SectionInfo()
			section.ID = 'CS2051.101'
			fl1.add_section( section )
			section.InstructorInfo = classes.InstructorInfo()
			section.enroll( 'chris' )
			section.InstructorInfo.Instructors.append( 'sjohnson' )
			section.Provider = 'OU'

			fl1 = fl1.Sections[0]

		self.Active = True
		def c(): return self
		adapt = component.queryAdapter( fl1, chat_interfaces.IMeetingContainer )

		# No active meeting fails.
		assert_that( adapt.enter_active_meeting( None, {} ), is_( none() ) )

		# Create active meeting
		d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'sjohnson' }
		assert_that( adapt.create_meeting_from_dict( None, d, c ), is_(self) )

		# Bad sender fails
		assert_that( adapt.enter_active_meeting( None, {'Creator': 'not_enrolled'} ), is_( none() ) )

		# Valid senders work
		# Student can enter...
		assert_that( adapt.enter_active_meeting( None, {'Creator': 'chris'} ), is_( self ) )
		# and if the instructor enters, new events are broadcast
		def add_occupant_names( *args, **kwargs ):
			assert_that( kwargs, has_entry( 'broadcast',  False ) )
			self.added_occupants = True
		self.add_occupant_names = add_occupant_names
		self.emit_enteredRoom = lambda *args: None
		self.emit_roomMembershipChanged = lambda *args: None

		assert_that( adapt.enter_active_meeting( None, {'Creator': 'sjohnson' } ), is_( self ) )
		assert_that( self, has_property( 'added_occupants', True ) )



if __name__ == '__main__':
#	import logging
#	logging.basicConfig()
#	logging.getLogger( 'nti.dataserver.chat' ).setLevel( logging.DEBUG )
	unittest.main(verbosity=3)
