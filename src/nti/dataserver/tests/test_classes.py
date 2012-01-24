#!/usr/bin/env python2.7
#pylint: disable=R0904


from hamcrest import assert_that, has_length, is_, has_item, has_entry, same_instance, is_not, has_key, contains
from hamcrest.library import has_property
from nti.dataserver.tests import provides

from zope.component import eventtesting

from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.classes import SectionInfo, ClassInfo
from zope.lifecycleevent import IObjectAddedEvent, IObjectRemovedEvent
from zope.container.interfaces import IContainerModifiedEvent

import mock_dataserver

class TestSection(mock_dataserver.ConfiguringTestBase):

	def test_enroll_events(self):
		eventtesting.setUp()
		eventtesting.clearEvents()
		assert_that( eventtesting.getEvents(), has_length( 0 ) )

		section = SectionInfo()
		section.enroll( 'foo' )

		assert_that( eventtesting.getEvents(), has_length( 2 ) )

		assert_that( eventtesting.getEvents( IObjectAddedEvent ), has_length( 1 ) )
		event = eventtesting.getEvents( IObjectAddedEvent )[0]
		assert_that( event.newName, is_( 'foo' ) )
		assert_that( event.object, is_( 'foo' ) )
		assert_that( event.newParent, is_( section._enrolled ) )
		assert_that( event.newParent.__parent__, is_( section ) )


		assert_that( eventtesting.getEvents( IContainerModifiedEvent ), has_length( 1 ) )
		event = eventtesting.getEvents( IContainerModifiedEvent )[0]
		assert_that( event.object, is_( section._enrolled ) )

# Example of subscribing to an event from one of these guys
from zope.component import provideHandler
from zope.component import adapter
from zope.interface.interfaces import IObjectEvent
_section_filtered_events = []
@adapter(nti_interfaces.IEnrolledContainer,IContainerModifiedEvent)
def _handle_section_event( *event ):

	_section_filtered_events.append( event )

def clearEvents():
	eventtesting.clearEvents()
	del _section_filtered_events[:]

class TestSection(mock_dataserver.ConfiguringTestBase):

	def setUp(self):
		super(TestSection,self).setUp()
		provideHandler( _handle_section_event )
		# Notice that pyramid configuration hooks up the event
		# notification process, so if eventtesting does it,
		# we get duplicates. All we need it to do is register
		# the catch-all handler
		provideHandler( eventtesting.events.append, (None,) )
		clearEvents()

	def tearDown(self):
		clearEvents()
		super(TestSection,self).tearDown()

	def test_migration(self):
		section = SectionInfo( ID='CS5201.101' )
		state = section.__getstate__()
		del state['_enrolled']
		state['Enrolled'] = ['jason.madden@nextthought.com']

		section.__setstate__( state )
		assert_that( list(section.Enrolled), has_item( 'jason.madden@nextthought.com' ) )
		assert_that( eventtesting.getEvents(), has_length( 2 ) )
		assert_that( eventtesting.getEvents( IObjectAddedEvent ),
					 has_item( has_property( 'newName', 'jason.madden@nextthought.com' ) ) )
		assert_that( eventtesting.getEvents( IContainerModifiedEvent )[0],
					 has_property( 'object', provides( nti_interfaces.IEnrolledContainer ) ) )

		assert_that( _section_filtered_events,
					 has_item( contains( provides( nti_interfaces.IEnrolledContainer ),
										 provides( IContainerModifiedEvent ) ) ) )

	@mock_dataserver.WithMockDS
	def test_can_enroll_from_external_ds(self):
		section = SectionInfo( ID='CS5201.101' )
		section_ext = datastructures.toExternalObject(section)
		section_ext['Enrolled'] = ['jason.madden@nextthought.com']

		self.ds.update_from_external_object( section, dict(section_ext) )
		assert_that( list(section.Enrolled), has_item( 'jason.madden@nextthought.com' ) )
		assert_that( eventtesting.getEvents(), has_length( 2 ) )
		assert_that( eventtesting.getEvents( IObjectAddedEvent ),
					 has_item( has_property( 'newName', 'jason.madden@nextthought.com' ) ) )
		assert_that( eventtesting.getEvents( IContainerModifiedEvent )[0],
					 has_property( 'object', provides( nti_interfaces.IEnrolledContainer ) ) )

		# Doing it a second time does nothing, no changes actually happen
		clearEvents()
		self.ds.update_from_external_object( section, dict(section_ext) )
		assert_that( list(section.Enrolled), has_item( 'jason.madden@nextthought.com' ) )
		assert_that( eventtesting.getEvents(), has_length( 0 ) )

	@mock_dataserver.WithMockDS
	def test_not_sending_enrolled_no_change(self):
		"If Enrolled is not sent, there is no change and no event."
		section = SectionInfo( ID='CS5201.101' )
		section.enroll( 'jason.madden@nextthought.com' )
		section_ext = datastructures.toExternalObject(section)
		clearEvents()
		del section_ext['Enrolled']

		self.ds.update_from_external_object( section, dict(section_ext) )
		assert_that( eventtesting.getEvents(), has_length( 0 ) )
		assert_that( list(section.Enrolled), has_item( 'jason.madden@nextthought.com' ) )

	@mock_dataserver.WithMockDS
	def test_sending_enrolled_delta_events(self):
		"Sending an Enrolled with different members generates events for the delta."
		section = SectionInfo( ID='CS5201.101' )
		section.enroll( 'jason.madden@nextthought.com' )
		section.enroll( 'foo@bar' )
		section_ext = datastructures.toExternalObject(section)
		clearEvents()

		# One still there, one gone, one added
		section_ext['Enrolled'] = ['jason.madden@nextthought.com', 'baz@bar']

		self.ds.update_from_external_object( section, dict(section_ext) )

		assert_that( list(section.Enrolled),
					 contains( 'baz@bar', 'jason.madden@nextthought.com' ) )

		# Four events: a pair for added, a pair for removed
		assert_that( eventtesting.getEvents(), has_length( 4 ) )
		assert_that( eventtesting.getEvents( IObjectAddedEvent ),
					 has_item( has_property( 'newName', 'baz@bar' ) ) )

		assert_that( eventtesting.getEvents( IObjectRemovedEvent ),
					 has_item( has_property( 'oldName', 'foo@bar' ) ) )


class TestClass(mock_dataserver.ConfiguringTestBase):

	def setUp(self):
		super(TestClass,self).setUp()
		# See notes in TestSection
		provideHandler( eventtesting.events.append, (None,) )
		clearEvents()

	def tearDown(self):
		clearEvents()
		super(TestClass,self).tearDown()

	def test_external(self):
		clazz = ClassInfo( ID='CS5201' )
		section = SectionInfo( ID='CS5201.501' )
		clazz.add_section( section )

		ext = datastructures.toExternalObject( clazz )
		assert_that( ext, has_entry( 'Sections', has_item( has_entry( 'ID', section.ID ) ) ) )

	def _assert_add_section_to_class( self, clazz, section=None, object_evt_type=IObjectAddedEvent ):
		assert_that( eventtesting.getEvents(), has_length( 2 ) )

		assert_that( eventtesting.getEvents( object_evt_type ), has_length( 1 ) )
		event = eventtesting.getEvents( object_evt_type )[0]
		if section:
			if object_evt_type == IObjectAddedEvent:
				assert_that( section.__parent__, is_( clazz._sections ) )
				assert_that( event.newName, is_( section.ID ) )
			assert_that( event.object, is_( section ) )

		if object_evt_type == IObjectAddedEvent:
			assert_that( event.newParent, is_( clazz._sections ) )
			assert_that( event.newParent.__parent__, is_( clazz ) )

		assert_that( eventtesting.getEvents( IContainerModifiedEvent ), has_length( 1 ) )
		event = eventtesting.getEvents( IContainerModifiedEvent )[0]
		assert_that( event,
					 has_property( 'object', provides( nti_interfaces.ISectionInfoContainer ) ) )
		assert_that( event.object, is_( clazz._sections ) )

	def test_migration(self):
		clazz = ClassInfo( ID='CS5201' )
		clazz.Provider = 'NTI'
		section = SectionInfo( ID='CS5201.101' )

		state = clazz.__getstate__()
		del state['_sections']
		state['Sections'] = [section]

		clazz.__setstate__( state )
		self._assert_add_section_to_class( clazz, section )


	def test_add_section_via_external(self):
		"We can add a section from the external dict. It fires events."
		clazz = ClassInfo( ID='CS5201' )
		clazz.Provider = 'NTI'
		section = SectionInfo( ID='CS5201.101' )

		clazz_ext = datastructures.toExternalObject( clazz )
		section_ext = datastructures.toExternalObject( section )

		clazz_ext['Sections'] = [section_ext]

		clazz.updateFromExternalObject( clazz_ext )
		assert_that( clazz[section.ID], is_( section ) )
		self._assert_add_section_to_class( clazz, clazz[section.ID] )

	def test_add_section_via_external_generates_id(self):
		"We can add a section from the external dict even if it has no ID. It fires events."
		clazz = ClassInfo( ID='CS5201' )
		clazz.Provider = 'NTI'
		section = SectionInfo()

		clazz_ext = datastructures.toExternalObject( clazz )
		section_ext = datastructures.toExternalObject( section )

		clazz_ext['Sections'] = [section_ext]

		clazz.updateFromExternalObject( clazz_ext )
		section.ID = 'CS5201.1'
		assert_that( clazz['CS5201.1'], is_( section ) )
		self._assert_add_section_to_class( clazz, clazz['CS5201.1'] )
		datastructures.toExternalObject( clazz )

		# Then again with a new one, preserving the first
		clearEvents()
		clazz_ext['Sections'].append( datastructures.toExternalObject( section ) )
		clazz.updateFromExternalObject( clazz_ext )
		section.ID = 'CS5201.2'
		assert_that( clazz['CS5201.2'], is_( section ) )
		self._assert_add_section_to_class( clazz, clazz['CS5201.2'] )
		datastructures.toExternalObject( clazz )

	@mock_dataserver.WithMockDS
	def test_add_section_via_external_through_ds(self):
		"We can add a section from the external dict using the DS even if it has no ID. It fires events."
		clazz = ClassInfo( ID='CS5201' )
		clazz.Provider = 'NTI'
		section = SectionInfo()

		clazz_ext = datastructures.toExternalObject( clazz )
		section_ext = datastructures.toExternalObject( section )
		assert_that( section_ext, is_not( has_key( 'ID' ) ) )
		clazz_ext['Sections'] = [section_ext]
		# The dictionary gets modified during this process
		self.ds.update_from_external_object( clazz, dict(clazz_ext) )

		section.ID = 'CS5201.1'
		assert_that( clazz['CS5201.1'], is_( section ) )
		assert_that( list(clazz.Sections), has_length( 1 ) )
		self._assert_add_section_to_class( clazz, clazz['CS5201.1'] )
		datastructures.toExternalObject( clazz )

		# Then again with a new one, preserving the first
		clearEvents()
		clazz_ext['Sections'].append( datastructures.toExternalObject( section ) )
		assert_that( clazz_ext['Sections'][0], is_not( has_key( 'ID' ) ) )
		assert_that( clazz_ext['Sections'][1], has_key( 'ID' ) )

		self.ds.update_from_external_object( clazz, dict(clazz_ext) )
		assert_that( list( clazz.Sections ), has_length( 2 ) )
		assert_that( clazz['CS5201.1'], is_(section) )
		section.ID = 'CS5201.2'
		assert_that( clazz['CS5201.2'], is_( section ) )
		self._assert_add_section_to_class( clazz, clazz['CS5201.2'] )
		datastructures.toExternalObject( clazz )

	def test_update_section_in_place(self):
		"Sending data for a section we already have updates existing section."
		clazz = ClassInfo( ID='CS5201' )
		section = SectionInfo( ID='CS5201.501' )
		clazz.add_section( section )

		clearEvents()

		clazz_ext = datastructures.toExternalObject( clazz )
		clazz_ext['Sections'][0]['Description'] = 'Cool section'

		clazz.updateFromExternalObject( clazz_ext )
		assert_that( clazz[section.ID], is_( same_instance( section ) ) )
		assert_that( clazz[section.ID].Description, is_( 'Cool section' ) )
		assert_that( eventtesting.getEvents(), has_length( 0 ) )

	@mock_dataserver.WithMockDS
	def test_update_section_in_place_via_ds(self):
		"Sending data through the DS for a section we already have updates existing section."
		clazz = ClassInfo( ID='CS5201' )
		section = SectionInfo( ID='CS5201.501' )
		clazz.add_section( section )

		clearEvents()

		clazz_ext = datastructures.toExternalObject( clazz )
		clazz_ext['Sections'][0]['Description'] = 'Cool section'

		self.ds.update_from_external_object( clazz, dict( clazz_ext ) )
		assert_that( clazz[section.ID], is_( same_instance( section ) ) )
		assert_that( clazz[section.ID].Description, is_( 'Cool section' ) )
		assert_that( eventtesting.getEvents(), has_length( 0 ) )

	def test_del_section_via_external(self):
		"Sending sections without a section deletes that section."
		clazz = ClassInfo( ID='CS5201' )
		section = SectionInfo( ID='CS5201.501' )
		clazz.add_section( section )
		clearEvents()

		clazz_ext = datastructures.toExternalObject( clazz )
		del clazz_ext['Sections']

		clazz.updateFromExternalObject( clazz_ext )
		assert_that( clazz._sections, has_length( 0 ) )
		assert_that( eventtesting.getEvents(), has_length( 2 ) )
		self._assert_add_section_to_class( clazz, section, IObjectRemovedEvent )

	def test_class_with_ext_oid_id_ntiid(self):
		"We workaround getting the external OID-based NTIID as our primary ID"
		clazz = ClassInfo()
		clazz.id = datastructures.to_external_ntiid_oid( clazz )
		datastructures.toExternalObject( clazz )

	def test_section_events(self):
		clazz = ClassInfo( ID='CS5201' )
		section = SectionInfo( ID='CS5201.501' )
		clazz.add_section( section )
		self._assert_add_section_to_class( clazz, section )

