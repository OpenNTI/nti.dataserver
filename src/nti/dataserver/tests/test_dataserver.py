#!/usr/bin/env python2.7



from hamcrest import assert_that, equal_to, is_, none, not_none, has_property, not_none
import mock_dataserver
from nose.tools import assert_raises

from nti.ntiids import ntiids
import nti.dataserver.contenttypes as contenttypes

from nti.externalization.oids import to_external_ntiid_oid, toExternalOID
import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver._Dataserver import run_job_in_site
import nti.dataserver

import transaction
import persistent
from zope import component
from zope import interface
from zope.traversing import interfaces as trv_interfaces, api as trv_api




class TestDataserver( mock_dataserver.ConfiguringTestBase ):

	def test_patched_traversal_api(self):
		assert nti.dataserver._patched_traversing, "No fixed version exists"

		@interface.implementer(trv_interfaces.ITraversable)
		class BrokenTraversable(object):
			def traverse( self, name, furtherPath ):
				getattr( self, u'\u2019', None ) # Raise unicode error


		with assert_raises(trv_interfaces.TraversalError):
			# Not a unicode error
			trv_api.traverseName( BrokenTraversable(), '' )

		assert_that( trv_api.traverseName( BrokenTraversable(), '', default=1 ), is_( 1 ) )



		with assert_raises(trv_interfaces.TraversalError):
			# Not a unicode error
			trv_api.traverseName( object(), u'\u2019' )

		assert_that( trv_api.traverseName( object(), u'\u2019', default=1 ), is_( 1 ) )

		with assert_raises(trv_interfaces.TraversalError):
			# Not a unicode error
			trv_api.traverseName( {}, u'\u2019' )

		assert_that( trv_api.traverseName( {}, u'\u2019', default=1 ), is_( 1 ) )

	@mock_dataserver.WithMockDS
	def test_run_job_in_site(self):
		runs = [0]
		def job():
			runs[0] = runs[0] + 1
			assert_that( component.getSiteManager(), has_property( '_p_jar', not_none() ) )
			return runs[0]

		i = run_job_in_site( job )
		assert_that( runs[0], is_( 1 ), "Only run once" )
		assert_that( i, is_( 1 ) )

		runs[0] = 0
		run_job_in_site( job, retries=10 )
		assert_that( runs[0], is_( 1 ), "Only run once" )

		def job():
			runs[0] = runs[0] + 1
			raise transaction.interfaces.TransientError( str(runs[0] ) )

		runs[0] = 0
		with self.assertRaises( transaction.interfaces.TransientError ):
			run_job_in_site( job )
		assert_that( runs[0], is_( 1 ), "Only run once" )

		runs[0] = 0
		with self.assertRaises( transaction.interfaces.TransientError ):
			run_job_in_site( job, retries=9 )
		# The first time, then 9 retries
		assert_that( runs[0], is_( 10 ), "Runs ten times" )

		def job():
			runs[0] = runs[0] + 1
			raise transaction.interfaces.DoomedTransaction( str(runs[0] ) )

		runs[0] = 0
		with self.assertRaises( transaction.interfaces.DoomedTransaction ):
			run_job_in_site( job, retries=9 )

		assert_that( runs[0], is_( 1 ), "Runs once" )

		def job():
			runs[0] = runs[0] + 1
			raise ValueError( str(runs[0] ) )

		runs[0] = 0
		with self.assertRaises( ValueError ):
			run_job_in_site( job, retries=9 )
		assert_that( runs[0], is_( 1 ), "Runs once" )

	@mock_dataserver.WithMockDS
	def test_find_content_type( self ):
		ds =  mock_dataserver.current_mock_ds
		# is_ doesn't work, that turns into class assertion
		assert_that( ds.find_content_type( 'Notes' ), equal_to( contenttypes.Note ) )
		assert_that( ds.find_content_type( 'Note' ), equal_to( contenttypes.Note ) )
		assert_that( ds.find_content_type( 'notes' ), equal_to( contenttypes.Note ) )

		assert_that( ds.find_content_type( 'quizresults' ), equal_to( contenttypes.quizresult ) )

		assert_that( ds.find_content_type( 'TestDataserver' ), is_( none() ) )

	@mock_dataserver.WithMockDSTrans
	def test_get_plain_oid(self):
		"""
		We can access an object given its OID bytes with no additional checks.
		"""
		obj = persistent.Persistent()
		mock_dataserver.current_transaction.add( obj )

		assert_that( mock_dataserver.current_mock_ds.get_by_oid( obj._p_oid ), is_( obj ) )
		assert_that( mock_dataserver.current_mock_ds.get_by_oid( '00000' ), is_( none() ) )

	@mock_dataserver.WithMockDSTrans
	def test_get_external_oid(self):
		"""
		We can access an object given its external OID string with no additional checks.
		"""
		obj = persistent.Persistent()
		mock_dataserver.current_transaction.add( obj )

		oid = toExternalOID( obj )
		assert_that( mock_dataserver.current_mock_ds.get_by_oid( oid ), is_( obj ) )


	@mock_dataserver.WithMockDSTrans
	def test_get_ntiid_oid_system_user(self):
		"""
		We can access an object given its OID in NTIID form when the provider
		is the system principal and the object has no creator. If it has a
		creator, then it must match.
		"""
		obj = contenttypes.Note()
		mock_dataserver.current_transaction.add( obj )

		oid = to_external_ntiid_oid( obj )
		assert_that( oid, is_( not_none() ) )
		assert_that( ntiids.get_provider( oid ), is_( nti_interfaces.SYSTEM_USER_NAME ) )

		assert_that( mock_dataserver.current_mock_ds.get_by_oid( oid ), is_( obj ) )

		# The system user is the only one that can access uncreated objects
		oid = ntiids.make_ntiid( provider='foo@bar', base=oid )
		assert_that( mock_dataserver.current_mock_ds.get_by_oid( oid ), is_( none() ) )

		# Now flip-flop the users around. The system user gets no
		# special treatment on created objects
		obj = contenttypes.Note()
		obj.creator = 'sjohnson@nextthought.com'
		mock_dataserver.current_transaction.add( obj )

		oid = to_external_ntiid_oid( obj )
		assert_that( ntiids.get_provider( oid ), is_( 'sjohnson@nextthought.com' ) )

		oid = ntiids.make_ntiid( provider=nti_interfaces.SYSTEM_USER_NAME, base=oid )
		assert_that( ntiids.get_provider( oid ), is_( nti_interfaces.SYSTEM_USER_NAME ) )

		assert_that( mock_dataserver.current_mock_ds.get_by_oid( oid ), is_( none() ) )

	@mock_dataserver.WithMockDSTrans
	def test_get_ntiid_oid_same_user(self):
		"""
		We can access an object given its OID in NTIID form when the creator
		matches the NTIID's provider.
		"""
		obj = contenttypes.Note()
		obj.creator = 's-johnson@nextthought.com' # Note the creator gets escaped
		mock_dataserver.current_transaction.add( obj )

		oid = to_external_ntiid_oid( obj )
		assert_that( ntiids.get_provider( oid ), is_( 's_johnson@nextthought.com' ) )
		assert_that( mock_dataserver.current_mock_ds.get_by_oid( oid ), is_( obj ) )

		oid = ntiids.make_ntiid( provider='some one else@nextthought.com', base=oid )
		assert_that( ntiids.get_provider( oid ), is_( 'some_one_else@nextthought.com' ) )

		assert_that( mock_dataserver.current_mock_ds.get_by_oid( oid ), is_( none() ) )

	@mock_dataserver.WithMockDSTrans
	def test_get_ntiid_oid_no_provider(self):
		"""
		The provider must match the creator, if there is one.
		"""
		obj = contenttypes.Note()
		obj.creator = 'sjohnson@nextthought.com'
		mock_dataserver.current_transaction.add( obj )

		oid = to_external_ntiid_oid( obj )
		assert_that( ntiids.get_provider( oid ), is_( 'sjohnson@nextthought.com' ) )
		# The provider is required
		oid_parts = ntiids.get_parts( oid )
		oid = ntiids.make_ntiid( nttype=oid_parts.nttype, specific=oid_parts.specific )
		assert_that( ntiids.get_provider( oid ), is_( none() ) )

		assert_that( mock_dataserver.current_mock_ds.get_by_oid( oid ), is_( none() ) )


	@mock_dataserver.WithMockDSTrans
	def test_get_ntiid_oid_diff_user(self):
		"""
		We can access an object given its OID bytes with no additional checks.
		"""
		obj = contenttypes.Note()
		obj.creator = 'sjohnson@nextthought.com'
		mock_dataserver.current_transaction.add( obj )

		oid = to_external_ntiid_oid( obj )
		oid = ntiids.make_ntiid( provider='someoneelse@nextthought.com', base=oid )
		assert_that( ntiids.get_provider( oid ), is_( 'someoneelse@nextthought.com' ) )

		assert_that( mock_dataserver.current_mock_ds.get_by_oid( oid ), is_( none() ) )
