#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not as does_not
from hamcrest import has_property
from hamcrest import has_key
from hamcrest import contains_string

from nose.tools import assert_raises

import nti.tests
from nti.tests import verifiably_provides
from nti.tests import is_false

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver',) )
tearDownModule = nti.tests.module_teardown

from zope import interface
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces
from nti.dataserver.users import Everyone
from nti.dataserver.users import User

def test_default_user_profile():
	user = User( username="foo@bar" )

	prof = interfaces.ICompleteUserProfile( user )
	assert_that( prof,
				 verifiably_provides( interfaces.ICompleteUserProfile ) )
	assert_that( prof,
				 has_property( 'avatarURL', contains_string( 'http://' ) ) )
	assert_that( prof,
				 has_property( 'opt_in_email_communication', is_false() ) )


	with assert_raises(interfaces.EmailAddressInvalid):
		prof.email = u"foo"

	prof.email = 'foo@bar.com'

	prof2 = interfaces.ICompleteUserProfile( user )
	assert_that( prof2.email, is_( 'foo@bar.com' ) )
	assert_that( prof,
				 verifiably_provides( interfaces.ICompleteUserProfile ) )

	# Because of inheritance, even if we ask for IFriendlyNamed, we get ICompleteUserProfile
	prof2 = interfaces.IFriendlyNamed( user )
	assert_that( prof2.email, is_( 'foo@bar.com' ) )
	assert_that( prof,
				 verifiably_provides( interfaces.ICompleteUserProfile ) )


def test_updating_realname_from_external():
	user = User( username="foo@bar" )

	user.updateFromExternalObject( {'realname': 'Foo Bar' } )

	prof = interfaces.ICompleteUserProfile( user )
	assert_that( prof,
				 has_property( 'realname', 'Foo Bar' ) )

	interface.alsoProvides( user, interfaces.IImmutableFriendlyNamed )
	user.updateFromExternalObject( {'realname': 'Changed Name' } )

	prof = interfaces.ICompleteUserProfile( user )
	assert_that( prof,
				 has_property( 'realname', 'Foo Bar' ) )


def test_updating_avatar_url_from_external():
	user = User( username="foo@bar" )

	user.updateFromExternalObject( {'avatarURL': 'http://localhost/avatarurl' } )

	prof = interfaces.ICompleteUserProfile( user )
	assert_that( prof,
				 has_property( 'avatarURL', 'http://localhost/avatarurl' ) )

def test_user_profile_with_legacy_dict():
	user = User( "foo@bar" )
	user._alias = 'bizbaz'
	user._realname = 'boo'

	prof = interfaces.ICompleteUserProfile( user )
	assert_that( prof, verifiably_provides( interfaces.ICompleteUserProfile ) )

	assert_that( prof, has_property( 'alias', 'bizbaz' ) )
	assert_that( prof, has_property( 'realname', 'boo' ) )

	prof.alias = 'haha'
	prof.realname = 'hehe'

	assert_that( prof, has_property( 'alias', 'haha' ) )
	assert_that( prof, has_property( 'realname', 'hehe' ) )


	assert_that( user.__dict__, does_not( has_key( '_alias' ) ) )
	assert_that( user.__dict__, does_not( has_key( '_realname' ) ) )

def test_everyone_names():
	everyone = Everyone()

	names = interfaces.IFriendlyNamed( everyone )
	assert_that( names, has_property( 'alias', 'Public' ) )
	assert_that( names, has_property( 'realname', 'Everyone' ) )
