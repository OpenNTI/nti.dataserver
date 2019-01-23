#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import same_instance
from hamcrest import contains_string
from hamcrest import greater_than_or_equal_to
from hamcrest.core.base_matcher import BaseMatcher

import tempfile
import unittest

from nti.dataserver.tests import  provides

from zope import component

from zope.interface.verify import verifyObject

from nti.dataserver import authorization as auth

from nti.dataserver import authorization_acl as auth_acl

from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.contenttypes import Note

from nti.dataserver.users import User
from nti.dataserver.users import FriendsList

try:
	# FIXME: I'm not really sure where this code should live
	from nti.appserver.pyramid_authorization import ZopeACLAuthorizationPolicy as ACLAuthorizationPolicy
except ImportError:
	from pyramid.authorization import ACLAuthorizationPolicy

from nti.dataserver.tests import mock_dataserver

class TestACLProviders(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

	@mock_dataserver.WithMockDSTrans
	def test_non_shared(self):
		n = Note()
		creator = User.create_user(username='sjohnson@nextthought.com')
		User.create_user(username='foo@bar')

		n.creator = creator

		acl_prov = nti_interfaces.IACLProvider(n)
		assert_that(acl_prov, provides(nti_interfaces.IACLProvider))
		verifyObject(nti_interfaces.IACLProvider, acl_prov)

		acl = acl_prov.__acl__
		assert_that(acl, has_length(greater_than_or_equal_to(2)))

		action, actor, permission = acl[0]
		assert_that(action, is_(nti_interfaces.ACE_ACT_ALLOW))
		assert_that(actor, provides(nti_interfaces.IPrincipal))
		assert_that(actor.id, is_(n.creator.username))
		assert_that(permission, provides(nti_interfaces.IPermission))
		assert_that(permission, is_(nti_interfaces.ALL_PERMISSIONS))

	@mock_dataserver.WithMockDSTrans
	def test_shared(self):
		creator = User.create_user(username='sjohnson@nextthought.com')
		target = User.create_user(username='foo@bar')

		n = Note()
		n.creator = creator
		n.addSharingTarget(target)

		acl_prov = nti_interfaces.IACLProvider(n)
		assert_that(acl_prov, provides(nti_interfaces.IACLProvider))
		verifyObject(nti_interfaces.IACLProvider, acl_prov)

		acl = acl_prov.__acl__
		assert_that(acl, has_length(greater_than_or_equal_to(3)))

		action, actor, permission = acl[0]
		assert_that(action, is_(nti_interfaces.ACE_ACT_ALLOW))
		assert_that(actor, provides(nti_interfaces.IPrincipal))
		assert_that(actor.id, is_(n.creator.username))
		assert_that(permission, provides(nti_interfaces.IPermission))
		assert_that(permission, is_(nti_interfaces.ALL_PERMISSIONS))

		action, actor, permission = acl[1]
		assert_that(action, is_(nti_interfaces.ACE_ACT_ALLOW))
		assert_that(actor, provides(nti_interfaces.IPrincipal))
		assert_that(actor.id, is_(list(n.sharingTargets)[0].username))
		assert_that(permission, has_length(1))
		assert_that(permission[0], provides(nti_interfaces.IPermission))
		assert_that(permission[0].id, is_('zope.View'))

	@mock_dataserver.WithMockDSTrans
	def test_pyramid_acl_authorization(self):
		"""
		Ensure our IPermission objects work with pyramid.
		"""
		creator = User.create_user(username='sjohnson@nextthought.com')
		target = User.create_user(username='foo@bar')
		n = Note()
		n.creator = creator
		n.addSharingTarget(target)

		acl_prov = nti_interfaces.IACLProvider(n)
		assert_that(acl_prov, provides(nti_interfaces.IACLProvider))
		verifyObject(nti_interfaces.IACLProvider, acl_prov)

		acl = acl_prov.__acl__
		assert_that(acl, has_length(greater_than_or_equal_to(3)))

		for action in (auth.ACT_CREATE, auth.ACT_DELETE, auth.ACT_UPDATE, auth.ACT_READ):
			assert_that(acl_prov, permits('sjohnson@nextthought.com', action))

		assert_that(acl_prov, permits('foo@bar', auth.ACT_READ))

		for action in (auth.ACT_CREATE, auth.ACT_DELETE, auth.ACT_UPDATE):
			assert_that(acl_prov, denies('foo@bar', action))

	@mock_dataserver.WithMockDSTrans
	def test_friends_list_acl_provider(self):
		friends_list = FriendsList("friends@bar")
		friends_list.creator = None

		# With no creator and no one enrolled, I have an ACL
		# that simply denies everything
		acl_prov = nti_interfaces.IACLProvider(friends_list)
		assert_that(acl_prov, provides(nti_interfaces.IACLProvider))
		verifyObject(nti_interfaces.IACLProvider, acl_prov)

		acl = acl_prov.__acl__
		assert_that(acl, has_length(1))
		assert_that(acl[0], is_(auth_acl.ace_denying(nti_interfaces.EVERYONE_GROUP_NAME,
													 nti_interfaces.ALL_PERMISSIONS)))

		# Given a creator and a member, the creator has all access
		# and the friend has read
		creator = User.create_user(self.ds, username='sjohnson@baz')
		friend = User.create_user(self.ds, username='friend@baz')

		friends_list.creator = creator
		friends_list.addFriend(friend)

		# The acl is cached though...
		assert_that(acl_prov.__acl__, is_(acl))
		# ... so we have to remove it before continuing
		del acl_prov.__acl__

		assert_that(acl_prov, permits('friend@baz',
									  auth.ACT_READ))

		assert_that(acl_prov, permits('sjohnson@baz',
									  auth.ACT_UPDATE))

		assert_that(acl_prov, denies('enemy@bar',
									  auth.ACT_READ))

		assert_that(acl_prov, denies('enrolled@bar',
									  auth.ACT_UPDATE))

class TestACE(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

	def test_to_from_string(self):
		# To string
		assert_that(auth_acl.ace_allowing('User', auth.ACT_CREATE).to_external_string(),
					is_('Allow:User:[\'nti.actions.create\']'))
		assert_that(auth_acl.ace_allowing('User', nti_interfaces.ALL_PERMISSIONS).to_external_string(),
					is_('Allow:User:All'))
		assert_that(auth_acl.ace_allowing('User', (auth.ACT_CREATE, auth.ACT_UPDATE)).to_external_string(),
					 is_('Allow:User:[\'nti.actions.create\', \'nti.actions.update\']'))

		assert_that(auth_acl.ace_denying('system.Everyone', (auth.ACT_CREATE, auth.ACT_UPDATE)).to_external_string(),
					is_('Deny:system.Everyone:[\'nti.actions.create\', \'nti.actions.update\']'))

		# From string
		assert_that(auth_acl.ace_from_string('Deny:system.Everyone:[\'nti.actions.create\', \'nti.actions.update\']'),
					is_(auth_acl.ace_denying('system.Everyone', (auth.ACT_CREATE, auth.ACT_UPDATE))))

		assert_that(auth_acl.ace_from_string('Allow:User:All'),
					is_(auth_acl.ace_allowing('User', nti_interfaces.ALL_PERMISSIONS)))

	def test_default(self):
		assert_that(auth_acl.ACL("foo"), is_(()))

	def test_add(self):

		ace1 = auth_acl.ace_allowing('User', auth.ACT_CREATE)
		ace2 = auth_acl.ace_denying('system.Everyone', (auth.ACT_CREATE, auth.ACT_UPDATE))

		acl = auth_acl.acl_from_aces((ace1,))
		acl2 = acl + ace2
		assert_that(acl2, is_not(same_instance(acl)))
		assert_that(acl2, has_length(2))
		assert_that(acl + acl2, has_length(3))

	def test_write_to_file(self):
		n = Note()
		n.creator = 'sjohnson@nextthought.com'

		acl_prov = nti_interfaces.IACLProvider(n)
		acl = acl_prov.__acl__
		acl.write_to_file('/dev/null')  # cover the string case

		temp_file = tempfile.TemporaryFile('w+')
		acl.write_to_file(temp_file)  # cover the fileobj case
		temp_file.seek(0)

		from_file = auth_acl.acl_from_file(temp_file)
		assert_that(from_file, is_(acl))

class TestHasPermission(unittest.TestCase):

	layer = mock_dataserver.SharedConfiguringTestLayer

	def setUp(self):
		super(TestHasPermission, self).setUp()
		n = Note()
		n.creator = 'sjohnson@nextthought.com'
		self.note = n

	def test_without_policy(self):
		result = auth_acl.has_permission(auth.ACT_CREATE, self.note, "sjohnson@nextthought.com")
		assert_that(bool(result), is_(False))
		assert_that(result, has_property('msg', 'No IAuthorizationPolicy installed'))

	def test_no_acl(self):
		result = auth_acl.has_permission(auth.ACT_CREATE, "no acl", "sjohnson@nextthought.com")
		assert_that(bool(result), is_(False))
		assert_that(result, has_property('msg', 'No ACL found'))

	def test_creator_allowed(self):
		policy = ACLAuthorizationPolicy()
		try:
			component.provideUtility(policy)
			result = auth_acl.has_permission(auth.ACT_CREATE, self.note, "sjohnson@nextthought.com", user_factory=lambda s: s)
			assert_that(bool(result), is_(True))
			assert_that(result, has_property('msg', contains_string('ACLAllowed')))
		finally:
			component.getGlobalSiteManager().unregisterUtility(policy)

from zope.security.permission import Permission

class Permits(BaseMatcher):

	def __init__(self, prin, perm, policy=ACLAuthorizationPolicy()):
		super(Permits, self).__init__()
		try:
			self.prin = (nti_interfaces.IPrincipal(prin),)
		except TypeError:
			try:
				self.prin = [nti_interfaces.IPrincipal(x) for x in prin]
			except TypeError:
				self.prin = prin
		self.perm = perm if nti_interfaces.IPermission.providedBy(perm) else Permission(perm)
		self.policy = policy

	def _matches(self, item):
		if not hasattr(item, '__acl__'):
			item = nti_interfaces.IACLProvider(item, item)
		return self.policy.permits(item,
									self.prin,
									self.perm)

	__description__ = 'ACL permitting '
	def describe_to(self, description):
		description.append_text(self.__description__) \
								.append_text(','.join([x.id for x in self.prin])) \
								.append_text(' permission ') \
								.append(self.perm.id)

	def describe_mismatch(self, item, mismatch_description):
		acl = getattr(item, '__acl__', None)
		if acl is None:
			acl = getattr(nti_interfaces.IACLProvider(item, item), '__acl__', None)

		mismatch_description.append_text('was ').append_description_of(item)
		if acl is not None and acl is not item:
			mismatch_description.append_text(' with acl ').append_description_of(acl)

class Denies(Permits):
	__description__ = 'ACL denying '

	def _matches(self, item):
		return not super(Denies, self)._matches(item)

def permits(prin, perm):
	return Permits(prin, perm)

def denies(prin, perm):
	return Denies(prin, perm)
