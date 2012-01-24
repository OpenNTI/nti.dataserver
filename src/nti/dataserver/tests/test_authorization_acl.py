#!/usr/bin/env python2.7
#pylint: disable=R0904

import unittest
from hamcrest import assert_that, has_length, contains_string, is_, same_instance, is_not
from nti.dataserver.tests import has_attr, provides
from zope.interface.verify import verifyObject
from zope import component

import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver import authorization as auth
from nti.dataserver import authorization_acl as auth_acl
from nti.dataserver.contenttypes import Note

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
		policy = ACLAuthorizationPolicy()

		n = Note()
		n.creator = 'sjohnson@nextthought.com'
		n.addSharingTarget( 'foo@bar', n.creator )

		acl_prov = nti_interfaces.IACLProvider( n )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length( 2 ) )

		for action in (auth.ACT_CREATE,auth.ACT_DELETE,auth.ACT_UPDATE,auth.ACT_READ):
			# Must be a principal, not a string; this policy does not auto-convert
			assert_that( policy.permits( acl_prov,
										 [nti_interfaces.IPrincipal('sjohnson@nextthought.com')],
										 action ),
						 is_( True ) )
			assert_that( policy.permits( acl_prov,
										 ['sjohnson@nextthought.com'],
										 action ),
						 is_( False ) )

		assert_that( policy.permits( acl_prov, [nti_interfaces.IPrincipal('foo@bar')], auth.ACT_READ ),
					 is_( True ) )

		for action in (auth.ACT_CREATE,auth.ACT_DELETE,auth.ACT_UPDATE):
			assert_that( policy.permits( acl_prov, [nti_interfaces.IPrincipal('foo@bar')], action ),
						 is_( False ) )

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
		policy = ACLAuthorizationPolicy()
		assert_that( policy.permits( acl_prov,
									 [nti_interfaces.IPrincipal('enrolled@bar')],
									 auth.ACT_READ ),
					is_( True ) )

		# and an instructor can modify it
		section.InstructorInfo.Instructors.append( "sjohnson@nti.com" )
		assert_that( policy.permits( acl_prov,
									 [nti_interfaces.IPrincipal('sjohnson@nti.com')],
									 auth.ACT_UPDATE ),
					is_( True ) )

		assert_that( policy.permits( acl_prov,
									 [nti_interfaces.IPrincipal('enrolled@bar')],
									 auth.ACT_READ ),
					is_( True ) )

		assert_that( policy.permits( acl_prov,
									 [nti_interfaces.IPrincipal('enrolled@bar')],
									 auth.ACT_UPDATE ),
					is_( False ) )

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
		policy = ACLAuthorizationPolicy()
		assert_that( policy.permits( acl_prov,
									 [nti_interfaces.IPrincipal('enrolled@bar')],
									 auth.ACT_READ ),
					is_( True ) )

		# and an instructor can modify it
		section.InstructorInfo.Instructors.append( "sjohnson@nti.com" )
		assert_that( policy.permits( acl_prov,
									 [nti_interfaces.IPrincipal('sjohnson@nti.com')],
									 auth.ACT_UPDATE ),
					is_( True ) )

		assert_that( policy.permits( acl_prov,
									 [nti_interfaces.IPrincipal('enrolled@bar')],
									 auth.ACT_READ ),
					is_( True ) )

		assert_that( policy.permits( acl_prov,
									 [nti_interfaces.IPrincipal('enrolled@bar')],
									 auth.ACT_UPDATE ),
					is_( False ) )
