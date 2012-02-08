#!/usr/bin/env python2.7
#pylint: disable=R0904

import unittest
from hamcrest import assert_that, has_length, contains_string, is_, same_instance, is_not
from hamcrest.core.base_matcher import BaseMatcher

from nti.dataserver.tests import has_attr, provides
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
		assert_that( actor.id, is_( n.sharingTargets[0] ) )
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

class Permits(BaseMatcher):

	def __init__( self, prin, perm, policy=ACLAuthorizationPolicy() ):
		super(Permits,self).__init__( )
		self.prin = nti_interfaces.IPrincipal( prin )
		self.perm = perm
		self.policy = policy

	def _matches( self, item ):
		return self.policy.permits( item, [self.prin], self.perm )

	def describe_to( self, description ):
		description.append_text( 'ACL permitting ') \
								 .append_text( self.prin.id ) \
								 .append_text( ' permission ' ) \
								 .append( self.perm.id )

	def describe_mismatch(self, item, mismatch_description):
		import pdb; pdb.set_trace()
		mismatch_description.append_text('was ').append_description_of(getattr( item, '__acl__', item ))

class Denies(Permits):

	def _matches( self, item ):
		return not super(Denies,self)._matches( item )

def permits( prin, perm ):
	return Permits( prin, perm )

def denies( prin, perm ):
	return Denies( prin, perm )
