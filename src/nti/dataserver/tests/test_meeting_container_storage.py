#!/usr/bin/env python2.7


from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance, has_length, none,
					  has_item, has_items)
import unittest
from zope import (interface, component)


import nti.dataserver as dataserver

import nti.dataserver.chat as chat
import nti.dataserver.chat_interfaces as chat_interfaces

import nti.dataserver.users as users
import nti.dataserver.providers as providers
import nti.dataserver.classes as classes
import nti.dataserver.ntiids as ntiids
import nti.dataserver.meeting_container_storage as mcs


from mock_dataserver import MockDataserver, WithMockDS, ConfiguringTestBase
import mock_dataserver


class TestMeetingContainer(ConfiguringTestBase):

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
			ds.root['users']['foo@bar'] = users.User( 'foo@bar', 'temp001' )

		mc = mcs.MeetingContainerStorage( ds )
		with mock_dataserver.mock_db_trans(ds):
			assert_that( ds.root['users'], has_key( 'foo@bar' ) )
			assert_that( mc.get( self.ID_FL1 ), is_( none() ) )
			assert_that( mc.get( None ), is_( none() ) )

	@WithMockDS
	def test_entity_with_list( self ):
		ds = self.ds
		with mock_dataserver.mock_db_trans(ds):
			user = users.User( 'foo@bar', 'temp001' )
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


class TestFriendsListAdaptor( ConfiguringTestBase ):

	@WithMockDS
	def test_create_and_empty( self ):
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

		self.Active = True
		def c(): return self
		adapt = component.queryAdapter( fl1, chat_interfaces.IMeetingContainer )

		# Missing occupants fails
		assert_that( adapt.create_meeting_from_dict( None, {}, c ), is_( none() ) )
		# Bad occupants fails
		assert_that( adapt.create_meeting_from_dict( None, {'Occupants': ['me']}, c ), is_( none() ) )

		# Dict with right occupants and tuple succeeds
		# creator is just occupant, not owner
		d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'friend@bar' }
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

		self.Active = True
		def c(): return self
		adapt = component.queryAdapter( fl1, chat_interfaces.IMeetingContainer )

		# No active meeting fails.
		assert_that( adapt.enter_active_meeting( None, {} ), is_( none() ) )

		# Create active meeting
		d = { 'Occupants': [('foo@bar', 1234)], 'Creator': 'friend@bar' }
		assert_that( adapt.create_meeting_from_dict( None, d, c ), is_(self) )


		# Bad sender fails
		assert_that( adapt.enter_active_meeting( None, {'Creator': 'me'} ), is_( none() ) )

		# Valid sender works
		assert_that( adapt.enter_active_meeting( None, {'Creator': user.username} ), is_( self ) )

class TestClassSectionAdapter( ConfiguringTestBase ):

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

			section = classes.SectionInfo()
			section.ID = 'CS2051.101'
			fl1.add_section( section )
			section.InstructorInfo = classes.InstructorInfo()
			section.enroll( 'chris' )
			section.InstructorInfo.Instructors.append( 'sjohnson' )
			section.Provider = 'OU'

			user.addContainedObject( fl1 )
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

			section = classes.SectionInfo()
			section.ID = 'CS2051.101'
			fl1.add_section( section )
			section.InstructorInfo = classes.InstructorInfo()
			section.enroll( 'chris' )
			section.InstructorInfo.Instructors.append( 'sjohnson' )
			section.Provider = 'OU'
			user.addContainedObject( fl1 )
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
		assert_that( adapt.enter_active_meeting( None, {'Creator': 'chris'} ), is_( self ) )
		assert_that( adapt.enter_active_meeting( None, {'Creator': 'sjohnson' } ), is_( self ) )




if __name__ == '__main__':
#	import logging
#	logging.basicConfig()
#	logging.getLogger( 'nti.dataserver.chat' ).setLevel( logging.DEBUG )
	unittest.main(verbosity=3)
