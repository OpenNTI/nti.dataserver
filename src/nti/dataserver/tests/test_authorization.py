#!/usr/bin/env python

#pylint: disable=R0904,W0402

from __future__ import print_function, absolute_import, unicode_literals

from hamcrest import assert_that, has_length, is_, same_instance, is_not
from hamcrest import contains
from hamcrest import has_property as has_attr
from hamcrest import has_entries

from nti.testing.matchers import provides
from nti.externalization.tests import externalizes

from nti.testing.matchers import validly_provides as verifiably_provides

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from zope import component

from zope.authentication.interfaces import IEveryoneGroup

from zope.interface.verify import verifyObject

from zope.security.interfaces import IParticipation

from zope.security.management import endInteraction
from zope.security.management import newInteraction
from zope.security.management import getInteraction
from zope.security.management import setSecurityPolicy

from zope.security.permission import Permission

from zope.securitypolicy.interfaces import IPrincipalPermissionManager

from zope.securitypolicy.zopepolicy import ZopeSecurityPolicy

import nti.dataserver.authorization as nauth
import nti.dataserver.users as users

import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver.interfaces import IPrincipal

from nti.appserver.pyramid_authorization import ZopeACLAuthorizationPolicy
from nti.dataserver.authorization_acl import has_permission
from nti.dataserver.authorization import ACT_READ

from nti.dataserver.contenttypes.note import Note


class TestAuthorization(DataserverLayerTest):

	def test_everyone_adapts(self):
		iprin = nti_interfaces.IPrincipal('system.Everyone')
		assert_that( iprin, provides( IEveryoneGroup ))

	def test_system_user_external(self):
		assert_that( nti_interfaces.system_user,
					 externalizes( has_entries( 'Class', 'SystemUser',
												'Username', nti_interfaces.SYSTEM_USER_NAME)))

	def test_user_adapts_to_group_member( self ):
		u = users.User( 'sjohnson@nextthought.com', 't' )
		pgm = nti_interfaces.IGroupMember( u )

		assert_that( pgm, verifiably_provides( nti_interfaces.IGroupMember ) )
		assert_that( list(pgm.groups), is_([]) )
		# As it happens, we get back as IGroupAwarePrincipal
		assert_that( pgm, verifiably_provides( nti_interfaces.IGroupAwarePrincipal ) )

		# Internally, this is implemented with annotations
		assert_that( u, has_attr( '__annotations__',
								  has_length( 1 ) ) )

		# And we're using the same objects so it works
		mutable = nti_interfaces.IMutableGroupMember( u )
		mutable.setGroups( ('abc',) )

		assert_that( pgm.groups, contains( nti_interfaces.IGroup('abc') ) )

		# additional roles
		rgm = component.getAdapter( u, nti_interfaces.IGroupMember, nauth.CONTENT_ROLE_PREFIX )
		assert_that( rgm, verifiably_provides( nti_interfaces.IGroupMember ) )
		assert_that( list(rgm.groups), is_([]) )

		assert_that( u, has_attr( '__annotations__',
								  has_length( 2 ) ) )

	def test_string_adapts_to_principal( self  ):
		# no-name
		iprin = nti_interfaces.IPrincipal( 'foo@bar' )
		assert_that( iprin, provides( nti_interfaces.IPrincipal ) )
		verifyObject( nti_interfaces.IPrincipal, iprin )

		#empty-string
		x = object()
		assert_that( nti_interfaces.IPrincipal( '', x ), is_(same_instance(x)))

		# named system, as component
		assert_that( component.getAdapter( nti_interfaces.SYSTEM_USER_NAME,
										   nti_interfaces.IPrincipal,
										   name=nti_interfaces.SYSTEM_USER_NAME ),
					 is_( same_instance( nti_interfaces.system_user ) ) )
		# system without name, as interface
		assert_that( nti_interfaces.IPrincipal( nti_interfaces.SYSTEM_USER_NAME ),
					 is_( same_instance( nti_interfaces.system_user ) ) )
		# everyone
		assert_that( nti_interfaces.IPrincipal( 'system.Everyone' ),
					 provides( nti_interfaces.IGroup ) )
		# everyone authenticated
		assert_that( nti_interfaces.IPrincipal( 'system.Authenticated' ),
					 provides( nti_interfaces.IGroup ) )
		assert_that( nti_interfaces.IPrincipal( 'system.Authenticated' ),
					 is_not( nti_interfaces.IPrincipal( 'system.Everyone' ) ) )

	def test_iprincipal_sorting(self):
		a = nti_interfaces.IPrincipal('a')
		b = nti_interfaces.IPrincipal('b')
		c = nti_interfaces.IPrincipal('c')
		d = nti_interfaces.IPrincipal('d')

		unsorted = [d, b, a, c]
		srtd = sorted(unsorted)
		assert_that( srtd, is_( [a, b, c, d] ) )

	def test_user_adapts_to_principal( self ):
		u = users.User( 'sjohnson@nextthought.com', 't' )
		iprin = nti_interfaces.IPrincipal( u )

		assert_that( iprin, verifiably_provides( nti_interfaces.IPrincipal ) )

		iprin2 = nti_interfaces.IGroupAwarePrincipal( u )
		assert_that( iprin2, verifiably_provides( nti_interfaces.IPrincipal ) )
		assert_that( iprin2, verifiably_provides( nti_interfaces.IGroupAwarePrincipal ) )
		# And, in fact, when we asked for an IPrincipal, we actually
		# got back an IGroupAwarePrincipal
		assert_that( iprin, verifiably_provides( nti_interfaces.IGroupAwarePrincipal ) )
		assert_that( iprin, is_( iprin2 ) )

		assert_that( iprin.id, is_( u.username ) )
		assert_that( iprin.description, is_( u.username ) )
		assert_that( iprin.title, is_( u.username ) )
		assert_that( repr(iprin), is_("_UserGroupAwarePrincipal('sjohnson@nextthought.com')") )
		assert_that( str(iprin), is_('sjohnson@nextthought.com') )

	def test_permission_methods(self):
		assert_that( nauth.ACT_CREATE, is_( Permission( nauth.ACT_CREATE.id ) ) )
		assert_that( nauth.ACT_CREATE, is_not( None ) )
		assert_that( str(nauth.ACT_CREATE), is_( nauth.ACT_CREATE.id ) )
		assert_that( repr(nauth.ACT_CREATE), is_( "Permission('nti.actions.create','','')" ) )

	def test_other_user_permissions(self):
		"""
		zope permissioning relies on the interaction to determine
		authorization. Ensure our `has_permission` check for other
		users properly handles interaction swapping.
		"""
		newInteraction(IParticipation(IPrincipal('third_party_perm_user')))
		new_note = Note()
		ppm = IPrincipalPermissionManager(new_note)
		ppm.grantPermissionToPrincipal(ACT_READ.id, 'third_party_perm_user')
		new_note.creator = 'other_user_creator'
		policy = ZopeACLAuthorizationPolicy()
		old_security_policy = setSecurityPolicy(ZopeSecurityPolicy)
		try:
			component.provideUtility(policy)
			result = has_permission(ACT_READ,
									new_note,
									"third_party_perm_user",
									user_factory=lambda s: s)
			assert_that(bool(result), is_(True), result)
			result = has_permission(ACT_READ,
									new_note,
									"third_party_unpermissioned_user",
									user_factory=lambda s: s)
			assert_that(bool(result), is_(False), result)
			current_user = getInteraction().participations[0].principal.id
			assert_that(current_user, is_('third_party_perm_user'))
		finally:
			setSecurityPolicy(old_security_policy)
			component.getGlobalSiteManager().unregisterUtility(policy)
			endInteraction()

