#!/usr/bin/env python
from __future__ import print_function, unicode_literals, absolute_import
#pylint: disable=R0904

import unittest
from hamcrest import assert_that, has_length,  is_
from hamcrest import greater_than_or_equal_to
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

try:
	# FIXME: I'm not really sure where this code should live
	from nti.appserver.pyramid_authorization import ZopeACLAuthorizationPolicy as ACLAuthorizationPolicy
except:
	from pyramid.authorization import ACLAuthorizationPolicy

from nti.dataserver.tests import mock_dataserver

class TestACLProviders(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

	@mock_dataserver.WithMockDSTrans
	def test_non_shared(self):
		n = Note()
		creator = User.create_user( username='sjohnson@nextthought.com' )
		target = User.create_user( username='foo@bar' )

		n.creator = creator

		acl_prov = nti_interfaces.IACLProvider( n )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length( greater_than_or_equal_to( 2 ) ) )

		action, actor, permission = acl[0]
		assert_that( action, is_( nti_interfaces.ACE_ACT_ALLOW ) )
		assert_that( actor, provides( nti_interfaces.IPrincipal ) )
		assert_that( actor.id, is_( n.creator.username ) )
		assert_that( permission, provides( nti_interfaces.IPermission ) )
		assert_that( permission, is_( nti_interfaces.ALL_PERMISSIONS ) )

	@mock_dataserver.WithMockDSTrans
	def test_shared( self ):
		creator = User.create_user( username='sjohnson@nextthought.com' )
		target = User.create_user( username='foo@bar' )

		n = Note()
		n.creator = creator
		n.addSharingTarget( target )

		acl_prov = nti_interfaces.IACLProvider( n )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length( greater_than_or_equal_to( 3 ) ) )

		action, actor, permission = acl[0]
		assert_that( action, is_( nti_interfaces.ACE_ACT_ALLOW ) )
		assert_that( actor, provides( nti_interfaces.IPrincipal ) )
		assert_that( actor.id, is_( n.creator.username ) )
		assert_that( permission, provides( nti_interfaces.IPermission ) )
		assert_that( permission, is_( nti_interfaces.ALL_PERMISSIONS ) )

		action, actor, permission = acl[1]
		assert_that( action, is_( nti_interfaces.ACE_ACT_ALLOW ) )
		assert_that( actor, provides( nti_interfaces.IPrincipal ) )
		assert_that( actor.id, is_( list(n.sharingTargets)[0].username ) )
		assert_that( permission, has_length( 1 ) )
		assert_that( permission[0], provides( nti_interfaces.IPermission ) )
		assert_that( permission[0].id, is_( 'zope.View' ) )


	@mock_dataserver.WithMockDSTrans
	def test_pyramid_acl_authorization( self ):
		"Ensure our IPermission objects work with pyramid."
		creator = User.create_user( username='sjohnson@nextthought.com' )
		target = User.create_user( username='foo@bar' )
		n = Note()
		n.creator = creator
		n.addSharingTarget( target )

		acl_prov = nti_interfaces.IACLProvider( n )
		assert_that( acl_prov, provides( nti_interfaces.IACLProvider ) )
		verifyObject( nti_interfaces.IACLProvider, acl_prov )

		acl = acl_prov.__acl__
		assert_that( acl, has_length(  greater_than_or_equal_to( 3 ) ) )

		for action in (auth.ACT_CREATE,auth.ACT_DELETE,auth.ACT_UPDATE,auth.ACT_READ):
			assert_that( acl_prov, permits( 'sjohnson@nextthought.com',
											action ) )

		assert_that( acl_prov, permits( 'foo@bar', auth.ACT_READ ) )

		for action in (auth.ACT_CREATE,auth.ACT_DELETE,auth.ACT_UPDATE):
			assert_that( acl_prov, denies( 'foo@bar', action ) )


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
		creator = User.create_user( self.ds, username='sjohnson@baz' )
		friend = User.create_user( self.ds, username='friend@baz' )

		friends_list.creator = creator
		friends_list.addFriend( friend )

		# The acl is cached though...
		assert_that( acl_prov.__acl__, is_( acl ) )
		# ... so we have to remove it before continuing
		del acl_prov.__acl__

		assert_that( acl_prov, permits( 'friend@baz',
										auth.ACT_READ ) )

		assert_that( acl_prov, permits( 'sjohnson@baz',
										auth.ACT_UPDATE ) )

		assert_that( acl_prov, denies( 'enemy@bar',
									   auth.ACT_READ ) )

		assert_that( acl_prov, denies( 'enrolled@bar',
									   auth.ACT_UPDATE ) )

class TestACE(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

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
		acl.write_to_file( '/dev/null' ) # cover the string case

		temp_file = tempfile.TemporaryFile( 'w+' )
		acl.write_to_file( temp_file ) # cover the fileobj case
		temp_file.seek( 0 )

		from_file = auth_acl.acl_from_file( temp_file )
		assert_that( from_file, is_( acl ) )

class TestHasPermission(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

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
		policy = ACLAuthorizationPolicy()
		try:
			component.provideUtility( policy  )
			result = auth_acl.has_permission( auth.ACT_CREATE, self.note, "sjohnson@nextthought.com", user_factory=lambda s: s )
			assert_that( bool(result), is_( True ) )
			assert_that( result, has_property( 'msg', contains_string('ACLAllowed' ) ) )
		finally:
			component.getGlobalSiteManager().unregisterUtility( policy )

from nti.contentlibrary.filesystem import FilesystemContentPackage, FilesystemContentUnit
from nti.contentlibrary.contentunit import _clear_caches

class TestLibraryEntryAclProvider(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

	@classmethod
	def setUpClass(cls):
		super(TestLibraryEntryAclProvider,cls).setUpClass()
		cls.temp_dir = tempfile.mkdtemp()
		cls.library_entry = FilesystemContentPackage()
		class Key(object):
			absolute_path = None
			bucket = None
			def __init__(self, bucket=None, name=None):
				self.absolute_path = name

			def readContents(self):
				try:
					with open(self.absolute_path, 'rb') as f:
						return f.read()
				except IOError:
					return None
		cls.library_entry.key = Key(name=os.path.join( cls.temp_dir, 'index.html' ))
		cls.library_entry.children = []
		cls.library_entry.make_sibling_key = lambda k: Key(name=os.path.join(cls.temp_dir, k))

		child = FilesystemContentUnit()
		child.key = Key(name=os.path.join( cls.temp_dir, 'child.html' ))
		child.make_sibling_key = lambda k: Key(name=os.path.join(cls.temp_dir, k))
		child.__parent__ = cls.library_entry
		child.ordinal = 1
		cls.library_entry.children.append( child )

		cls.acl_path = os.path.join( cls.temp_dir, '.nti_acl' )
		component.provideUtility( ACLAuthorizationPolicy() )

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree( cls.temp_dir )
		super(TestLibraryEntryAclProvider,cls).tearDownClass()

	def setUp(self):
		super(TestLibraryEntryAclProvider,self).setUp()
		# Our use of a layer prevents our setUpClass from running
		if not hasattr(self, 'library_entry'):
			self.setUpClass()

		self.library_entry.ntiid = None
		try:
			os.unlink( self.acl_path )
		except OSError:
			pass

	def test_no_acl_file(self):
		acl_prov = nti_interfaces.IACLProvider( self.library_entry )
		assert_that( acl_prov, permits( nti_interfaces.AUTHENTICATED_GROUP_NAME,
										auth.ACT_READ ) )

	def test_malformed_acl_file_denies_all(self):
		with open( self.acl_path, 'w' ) as f:
			f.write( "This file is invalid" )
		acl_prov = nti_interfaces.IACLProvider( self.library_entry )
		assert_that( acl_prov, denies( nti_interfaces.AUTHENTICATED_GROUP_NAME,
										auth.ACT_READ ) )


	def test_specific_acl_file(self):
		with open( self.acl_path, 'w' ) as f:
			f.write( "Allow:User:[nti.actions.create]\n" )
			f.write( " # This line has a comment\n" )
			f.write( "  \n" ) #This line is blank
			f.flush()

		for context in self.library_entry, self.library_entry.children[0]:
			__traceback_info__ = context
			acl_prov = nti_interfaces.IACLProvider( context )
			assert_that( acl_prov, permits( "User", auth.ACT_CREATE ) )
			assert_that( acl_prov, denies( "OtherUser", auth.ACT_CREATE ) )


		# Now, with an NTIID
		self.library_entry.ntiid = 'tag:nextthought.com,2011-10:PRMIA-HTML-Volume_III.A.2_converted.the_prm_handbook_volume_iii'
		acl_prov = nti_interfaces.IACLProvider( self.library_entry )
		assert_that( acl_prov, permits( "User", auth.ACT_CREATE ) )
		assert_that( acl_prov, denies( "OtherUser", auth.ACT_CREATE ) )

		assert_that( acl_prov, permits( "content-role:prmia:Volume_III.A.2_converted.the_prm_handbook_volume_iii".lower(), auth.ACT_READ ) )
		assert_that( acl_prov, permits( nti_interfaces.IGroup("content-role:prmia:Volume_III.A.2_converted.the_prm_handbook_volume_iii".lower()), auth.ACT_READ ) )

		# Now I can write another user in for access to just the child entry
		with open( self.acl_path + '.1', 'w' ) as f:
			f.write( 'Allow:OtherUser:All\n' )
		_clear_caches()

		# Nothing changed an the top level
		context = self.library_entry
		acl_prov = nti_interfaces.IACLProvider( context )
		assert_that( acl_prov, permits( "User", auth.ACT_CREATE ) )
		assert_that( acl_prov, denies( "OtherUser", auth.ACT_CREATE ) )

		# But the child level now allows access
		context = self.library_entry.children[0]
		acl_prov = nti_interfaces.IACLProvider( context )
		assert_that( acl_prov, permits( "User", auth.ACT_CREATE ) )
		assert_that( acl_prov, permits( "OtherUser", auth.ACT_CREATE ) )

		# The same applies if it is at the 'default' location
		os.rename( self.acl_path + '.1', self.acl_path + '.default' )
		acl_prov = nti_interfaces.IACLProvider( context )
		assert_that( acl_prov, permits( "User", auth.ACT_CREATE ) )
		assert_that( acl_prov, permits( "OtherUser", auth.ACT_CREATE ) )



from zope.security.permission import Permission
class Permits(BaseMatcher):

	def __init__( self, prin, perm, policy=ACLAuthorizationPolicy() ):
		super(Permits,self).__init__( )
		try:
			self.prin = (nti_interfaces.IPrincipal( prin ),)
		except TypeError:
			self.prin = prin
		self.perm = perm if nti_interfaces.IPermission.providedBy( perm ) else Permission( perm )
		self.policy = policy

	def _matches( self, item ):
		if not hasattr( item, '__acl__' ):
			item = nti_interfaces.IACLProvider( item, item )
		return self.policy.permits( item,
									self.prin,
									self.perm )

	__description__ = 'ACL permitting '
	def describe_to( self, description ):
		description.append_text( self.__description__ ) \
								 .append_text( ','.join([x.id for x in self.prin] )) \
								 .append_text( ' permission ' ) \
								 .append( self.perm.id )

	def describe_mismatch(self, item, mismatch_description):
		acl = getattr( item, '__acl__', None )
		if acl is None:
			acl = getattr( nti_interfaces.IACLProvider( item, item ), '__acl__', None )

		mismatch_description.append_text('was ').append_description_of( item )
		if acl is not None and acl is not item:
			mismatch_description.append_text( ' with acl ').append_description_of( acl )

class Denies(Permits):
	__description__ = 'ACL denying '
	def _matches( self, item ):
		return not super(Denies,self)._matches( item )

def permits( prin, perm ):
	return Permits( prin, perm )

def denies( prin, perm ):
	return Denies( prin, perm )
