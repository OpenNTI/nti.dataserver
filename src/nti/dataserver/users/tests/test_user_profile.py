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
from hamcrest import has_entry

from nose.tools import assert_raises

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.testing.matchers import verifiably_provides
from nti.testing.matchers import is_false
from nti.dataserver.tests import mock_dataserver


from zope import interface
from zope.security.interfaces import IPrincipal

from nti.dataserver.users import interfaces
from nti.dataserver.users import Everyone
from nti.dataserver.users import User
from nti.externalization.externalization import to_external_object

class TestUserProfile(DataserverLayerTest):

	def test_email_address_invalid_domain(self):
		with assert_raises(interfaces.EmailAddressInvalid):
			interfaces._checkEmailAddress( 'poop@poop.poop' ) # real-world example

		interfaces._checkEmailAddress( 'poop@poop.poop.com' )
		interfaces._checkEmailAddress( 'poop@poop.poop.co' )

	def test_default_user_profile(self):
		user = User( username="foo@bar" )

		prof = interfaces.ICompleteUserProfile( user )
		assert_that( prof,
					 verifiably_provides( interfaces.ICompleteUserProfile ) )
		assert_that( prof,
					 has_property( 'avatarURL', contains_string( 'http://' ) ) )
		assert_that( prof,
					 has_property( 'opt_in_email_communication', is_false() ) )

		# We can get to the principal representing the user
		assert_that( IPrincipal(prof), has_property('id', user.username))

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

		# We can get to the email address
		assert_that( interfaces.IEmailAddressable(user), has_property('email', 'foo@bar.com'))


	def test_non_blank_fields(self):
		user = User( username="foo@bar" )

		prof = interfaces.ICompleteUserProfile( user )

		for field in ('about', 'affiliation', 'role', 'location', 'description'):
			with assert_raises(interfaces.FieldCannotBeOnlyWhitespace):
				setattr( prof, field, '   ' ) # spaces
			with assert_raises(interfaces.FieldCannotBeOnlyWhitespace):
				setattr( prof, field, '\t' ) # tab

			setattr( prof, field, '  \t bc' )

	def test_updating_realname_from_external(self):
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


	def test_updating_avatar_url_from_external(self):
		user = User( username="foo@bar" )

		user.updateFromExternalObject( {'avatarURL': 'http://localhost/avatarurl' } )

		prof = interfaces.ICompleteUserProfile( user )
		assert_that( prof,
					 has_property( 'avatarURL', 'http://localhost/avatarurl' ) )

	def test_user_profile_with_legacy_dict(self):
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

	def test_everyone_names(self):
		everyone = Everyone()

		names = interfaces.IFriendlyNamed( everyone )
		assert_that( names, has_property( 'alias', 'Public' ) )
		assert_that( names, has_property( 'realname', 'Everyone' ) )

	@mock_dataserver.WithMockDSTrans
	def test_externalizing_extended_fields(self):
		user = User.create_user( username="foo@bar" )

		ext_user = to_external_object( user )
		assert_that( ext_user, has_entry( 'location', None ) )

		prof = interfaces.ICompleteUserProfile( user )
		prof.location = 'foo bar'

		ext_user = to_external_object( user )
		assert_that( ext_user, has_entry( 'location', 'foo bar' ) )
