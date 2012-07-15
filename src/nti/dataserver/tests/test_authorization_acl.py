#!/usr/bin/env python2.7
from __future__ import print_function, unicode_literals
#pylint: disable=R0904


from hamcrest import assert_that, has_length,  is_
from hamcrest import is_not, same_instance
from hamcrest import has_property
from hamcrest import contains_string
from hamcrest.core.base_matcher import BaseMatcher
import tempfile
import shutil
import os

from nti.dataserver.tests import  provides
from zope.interface.verify import verifyObject
from zope import component

import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver import authorization as auth
from nti.dataserver import authorization_acl as auth_acl
from nti.dataserver.contenttypes import Note
from nti.dataserver.users import User, FriendsList


from pyramid.authorization import ACLAuthorizationPolicy

import mock_dataserver

class TestShareableACLProvider(mock_dataserver.ConfiguringTestBase):

	def test_non_shared(self):
		n = Note()
		n.creator = 'sjohnson@nextthought.com'

		acl_prov = nti_interfaces.IACLProvider( n )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length( 1 ) )

		action, actor, permission = acl[0]
		assert_that( action, is_( nti_interfaces.ACE_ACT_ALLOW ) )
		assert_that( actor, provides( nti_interfaces.IPrincipal ) )
		assert_that( actor.id, is_( n.creator ) )
		assert_that( permission, provides( nti_interfaces.IPermission ) )
		assert_that( permission, is_( nti_interfaces.ALL_PERMISSIONS ) )

	def test_shared( self ):
		n = Note()
		n.creator = 'sjohnson@nextthought.com'
		n.addSharingTarget( 'foo@bar', n.creator )

		acl_prov = nti_interfaces.IACLProvider( n )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length( 2 ) )

		action, actor, permission = acl[0]
		assert_that( action, is_( nti_interfaces.ACE_ACT_ALLOW ) )
		assert_that( actor, provides( nti_interfaces.IPrincipal ) )
		assert_that( actor.id, is_( n.creator ) )
		assert_that( permission, provides( nti_interfaces.IPermission ) )
		assert_that( permission, is_( nti_interfaces.ALL_PERMISSIONS ) )

		action, actor, permission = acl[1]
		assert_that( action, is_( nti_interfaces.ACE_ACT_ALLOW ) )
		assert_that( actor, provides( nti_interfaces.IPrincipal ) )
		assert_that( actor.id, is_( list(n.sharingTargets)[0] ) )
		assert_that( permission, has_length( 1 ) )
		assert_that( permission[0], provides( nti_interfaces.IPermission ) )
		assert_that( permission[0].id, is_( 'zope.View' ) )


	def test_pyramid_acl_authorization( self ):
		"Ensure our IPermission objects work with pyramid."

		n = Note()
		n.creator = 'sjohnson@nextthought.com'
		n.addSharingTarget( 'foo@bar', n.creator )

		acl_prov = nti_interfaces.IACLProvider( n )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length( 2 ) )

		for action in (auth.ACT_CREATE,auth.ACT_DELETE,auth.ACT_UPDATE,auth.ACT_READ):
			assert_that( acl_prov, permits( 'sjohnson@nextthought.com',
											action ) )

		assert_that( acl_prov, permits( 'foo@bar', auth.ACT_READ ) )

		for action in (auth.ACT_CREATE,auth.ACT_DELETE,auth.ACT_UPDATE):
			assert_that( acl_prov, denies( 'foo@bar', action ) )

from .. import classes

class TestSectionInfoACLProvider(mock_dataserver.ConfiguringTestBase):
	def test_section_info_acl_provider(self):
		section = classes.SectionInfo()
		# With no instructors, no creator and no one enrolled, I have an ACL
		# that simply denies everything
		acl_prov = nti_interfaces.IACLProvider( section )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length( 2 ) )
		assert_that( acl[0], is_(auth_acl.ace_allowing( 'role:NTI.Admin', nti_interfaces.ALL_PERMISSIONS ) ) )
		assert_that( acl[1], is_(auth_acl.ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ) ) )

		# Some people enrolled should be able to view it
		section.enroll( 'enrolled@bar' )
		assert_that( acl_prov, permits( 'enrolled@bar',
										auth.ACT_READ ) )

		# and an instructor can modify it
		section.InstructorInfo.Instructors.append( "sjohnson@nti.com" )
		assert_that( acl_prov, permits( 'sjohnson@nti.com',
										auth.ACT_UPDATE ) )

		assert_that( acl_prov, permits( 'enrolled@bar',
										auth.ACT_READ ) )

		assert_that( acl_prov, denies( 'enrolled@bar',
									   auth.ACT_UPDATE ) )

class TestClassInfoACLProvider(mock_dataserver.ConfiguringTestBase):
	def test_class_info_acl_provider(self):
		klass = classes.ClassInfo()
		section = classes.SectionInfo()
		section.ID = 'CS5201.501'
		# With no instructors, no creator and no one enrolled, I have an ACL
		# that simply denies everything
		acl_prov = nti_interfaces.IACLProvider( klass )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		# At this point, there's no provider set, so nothing changes
		assert_that( acl, has_length( 1 ) )
		assert_that( acl[0], is_(auth_acl.ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ) ) )
		# Give it a section, nothing changes because the section is empty
		# except that we inherit a provider ACL from the section
		# TODO: Is that right? We should probably be forcing
		# consistency among providers
		klass.add_section( section )
		acl = acl_prov.__acl__
		assert_that( acl, has_length( 2 ) )
		assert_that( acl[0], is_(auth_acl.ace_allowing( 'role:NTI.Admin', nti_interfaces.ALL_PERMISSIONS ) ) )
		assert_that( acl[1], is_(auth_acl.ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ) ) )

		# But now start filling in the section and people start gaining
		# rights.
		# Some people enrolled should be able to view it
		section.enroll( 'enrolled@bar' )

		assert_that( acl_prov, permits( 'enrolled@bar',
										auth.ACT_READ ) )

		# and an instructor can modify it
		section.InstructorInfo.Instructors.append( "sjohnson@nti.com" )
		assert_that( acl_prov, permits( 'sjohnson@nti.com',
										auth.ACT_UPDATE ) )

		assert_that( acl_prov, permits( 'enrolled@bar',
										auth.ACT_READ ) )

		assert_that( acl_prov, denies( 'enrolled@bar',
									   auth.ACT_UPDATE ) )

class TestFriendsListACLProvider(mock_dataserver.ConfiguringTestBase):

	@mock_dataserver.WithMockDSTrans
	def test_friends_list_acl_provider(self):
		friends_list = FriendsList( "friends@bar" )
		friends_list.creator = None

		# With no creator and no one enrolled, I have an ACL
		# that simply denies everything
		acl_prov = nti_interfaces.IACLProvider( friends_list )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length( 1 ) )
		assert_that( acl[0], is_(auth_acl.ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ) ) )

		# Given a creator and a member, the creator has all access
		# and the friend has read
		creator = User( 'sjohnson@baz' )
		friend = User( 'friend@baz' )

		friends_list.creator = creator
		friends_list.addFriend( friend )

		assert_that( acl_prov, permits( 'friend@baz',
										auth.ACT_READ ) )

		assert_that( acl_prov, permits( 'sjohnson@baz',
										auth.ACT_UPDATE ) )

		assert_that( acl_prov, denies( 'enemy@bar',
									   auth.ACT_READ ) )

		assert_that( acl_prov, denies( 'enrolled@bar',
									   auth.ACT_UPDATE ) )

class TestACE(mock_dataserver.ConfiguringTestBase):

	def test_to_from_string(self):
		# To string
		assert_that( auth_acl.ace_allowing( 'User', auth.ACT_CREATE ).to_external_string(),
					 is_( 'Allow:User:[\'nti.actions.create\']' ) )
		assert_that( auth_acl.ace_allowing( 'User', nti_interfaces.ALL_PERMISSIONS ).to_external_string(),
					 is_( 'Allow:User:All' ) )
		assert_that( auth_acl.ace_allowing( 'User', (auth.ACT_CREATE,auth.ACT_UPDATE) ).to_external_string(),
					 is_( 'Allow:User:[\'nti.actions.create\', \'nti.actions.update\']' ) )

		assert_that( auth_acl.ace_denying( 'system.Everyone', (auth.ACT_CREATE,auth.ACT_UPDATE) ).to_external_string(),
					 is_( 'Deny:system.Everyone:[\'nti.actions.create\', \'nti.actions.update\']' ) )

		# From string
		assert_that( auth_acl.ace_from_string('Deny:system.Everyone:[\'nti.actions.create\', \'nti.actions.update\']' ),
					 is_( auth_acl.ace_denying( 'system.Everyone', (auth.ACT_CREATE,auth.ACT_UPDATE) ) ) )

		assert_that( auth_acl.ace_from_string('Allow:User:All' ),
					 is_( auth_acl.ace_allowing( 'User', nti_interfaces.ALL_PERMISSIONS ) ) )

	def test_default(self):
		assert_that( auth_acl.ACL( "foo" ), is_( () ) )

	def test_add(self):

		ace1 = auth_acl.ace_allowing( 'User', auth.ACT_CREATE )
		ace2 = auth_acl.ace_denying( 'system.Everyone', (auth.ACT_CREATE,auth.ACT_UPDATE) )

		acl = auth_acl.acl_from_aces( (ace1,) )
		acl2 = acl + ace2
		assert_that( acl2, is_not( same_instance( acl ) ) )
		assert_that( acl2, has_length( 2 ) )
		assert_that( acl + acl2, has_length( 3 ) )

	def test_write_to_file( self ):
		n = Note()
		n.creator = 'sjohnson@nextthought.com'

		acl_prov = nti_interfaces.IACLProvider( n )
		acl = acl_prov.__acl__
		acl.write_to_file( '/dev/null' )

		temp_file = tempfile.TemporaryFile( 'w+' )
		acl.write_to_file( temp_file )
		temp_file.seek( 0 )

		from_file = auth_acl.acl_from_file( temp_file )
		assert_that( from_file, is_( acl ) )

class TestHasPermission(mock_dataserver.ConfiguringTestBase):

	def setUp(self):
		super(TestHasPermission,self).setUp()
		n = Note()
		n.creator = 'sjohnson@nextthought.com'
		self.note = n

	def test_without_policy(self):
		result = auth_acl.has_permission( auth.ACT_CREATE, self.note, "sjohnson@nextthought.com" )
		assert_that( bool(result), is_( False ) )
		assert_that( result, has_property( 'msg', 'No IAuthorizationPolicy installed' ) )

	def test_no_acl(self):
		result = auth_acl.has_permission( auth.ACT_CREATE, "no acl", "sjohnson@nextthought.com" )
		assert_that( bool(result), is_( False ) )
		assert_that( result, has_property( 'msg', 'No ACL found' ) )

	def test_creator_allowed(self):
		component.provideUtility( ACLAuthorizationPolicy() )
		result = auth_acl.has_permission( auth.ACT_CREATE, self.note, "sjohnson@nextthought.com", user_factory=lambda s: s )
		assert_that( bool(result), is_( True ) )
		assert_that( result, has_property( 'msg', contains_string('ACLAllowed' ) ) )

from nti.contentlibrary.contentunit import FilesystemContentPackage

class TestLibraryEntryAclProvider(mock_dataserver.ConfiguringTestBase):

	def setUp(self):
		super(TestLibraryEntryAclProvider,self).setUp()
		self.temp_dir = tempfile.mkdtemp()
		self.library_entry = FilesystemContentPackage()
		self.library_entry.filename = os.path.join( self.temp_dir, 'index.html' )

		component.provideUtility( ACLAuthorizationPolicy() )

	def tearDown(self):
		shutil.rmtree( self.temp_dir )
		super(TestLibraryEntryAclProvider,self).tearDown()

	def test_no_acl_file(self):
		acl_prov = nti_interfaces.IACLProvider( self.library_entry )
		assert_that( acl_prov, permits( nti_interfaces.AUTHENTICATED_GROUP_NAME,
										auth.ACT_READ ) )

	def test_malformed_acl_file_denies_all(self):
		with open( os.path.join( self.temp_dir, '.nti_acl' ), 'w' ) as f:
			f.write( "This file is invalid" )
		acl_prov = nti_interfaces.IACLProvider( self.library_entry )
		assert_that( acl_prov, denies( nti_interfaces.AUTHENTICATED_GROUP_NAME,
										auth.ACT_READ ) )


	def test_specific_acl_file(self):
		with open( os.path.join( self.temp_dir, '.nti_acl' ), 'w' ) as f:
			f.write( "Allow:User:[nti.actions.create]" )
		acl_prov = nti_interfaces.IACLProvider( self.library_entry )
		assert_that( acl_prov, permits( "User", auth.ACT_CREATE ) )
		assert_that( acl_prov, denies( "OtherUser", auth.ACT_CREATE ) )

		assert_that( bool(auth_acl.has_permission(auth.ACT_CREATE, self.library_entry, "User", user_factory=lambda s: s)),
					 is_( True ) )
		assert_that( bool(auth_acl.has_permission(auth.ACT_CREATE, self.library_entry, "OtherUser", user_factory=lambda s: s)),
					 is_( False ) )

		assert_that( bool(auth_acl.has_permission(auth.ACT_CREATE, acl_prov, "User", user_factory=lambda s: s)),
					 is_( True ) )
		assert_that( bool(auth_acl.has_permission(auth.ACT_CREATE, acl_prov, "OtherUser", user_factory=lambda s: s)),
					 is_( False ) )

from zope.security.permission import Permission
class Permits(BaseMatcher):

	def __init__( self, prin, perm, policy=ACLAuthorizationPolicy() ):
		super(Permits,self).__init__( )
		self.prin = nti_interfaces.IPrincipal( prin )
		self.perm = perm if nti_interfaces.IPermission.providedBy( perm ) else Permission( perm )
		self.policy = policy

	def _matches( self, item ):
		if not hasattr( item, '__acl__' ):
			item = nti_interfaces.IACLProvider( item, default=item )
		return self.policy.permits( item, [self.prin], self.perm )

	def describe_to( self, description ):
		description.append_text( 'ACL permitting ') \
								 .append_text( self.prin.id ) \
								 .append_text( ' permission ' ) \
								 .append( self.perm.id )

	def describe_mismatch(self, item, mismatch_description):
		mismatch_description.append_text('was ').append_description_of(getattr( item, '__acl__', item ))

class Denies(Permits):

	def _matches( self, item ):
		return not super(Denies,self)._matches( item )

def permits( prin, perm ):
	return Permits( prin, perm )

def denies( prin, perm ):
	return Denies( prin, perm )
