#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

from nose.tools import assert_raises

import unittest

from zope import interface
from zope.security.interfaces import IPrincipal

from nti.dataserver.users import User
from nti.dataserver.users import Everyone
from nti.dataserver.users import interfaces

from nti.dataserver.users.user_profile import Education
from nti.dataserver.users.user_profile import ProfessionalPosition

from nti.externalization import internalization
from nti.externalization.externalization import to_external_object

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.testing.matchers import is_false
from nti.testing.matchers import verifiably_provides

from nti.dataserver.tests import mock_dataserver

class TestUserProfile(DataserverLayerTest):

	def test_email_address_invalid_domain(self):
		with assert_raises(interfaces.EmailAddressInvalid):
			interfaces._checkEmailAddress('poop@poop.poop')  # real-world example

		interfaces._checkEmailAddress('poop@poop.poop.com')
		interfaces._checkEmailAddress('poop@poop.poop.co')

	def test_default_user_profile(self):
		user = User(username="foo@bar")

		prof = interfaces.ICompleteUserProfile(user)
		assert_that(prof,
					verifiably_provides(interfaces.ICompleteUserProfile))
		assert_that(prof,
					has_property('avatarURL', is_(none())))
		assert_that(prof,
					has_property('backgroundURL', is_(none())))
		assert_that(prof,
					has_property('opt_in_email_communication', is_false()))

		assert_that(prof,
					verifiably_provides(interfaces.ISocialMediaProfile))
		assert_that(prof,
					has_property('twitter', is_(none())))
		assert_that(prof,
					has_property('facebook', is_(none())))

		assert_that(prof,
					verifiably_provides(interfaces.IEducationProfile))
		assert_that(prof,
					has_property('education', is_(none())))

		assert_that(prof,
					verifiably_provides(interfaces.IInterestProfile))
		assert_that(prof,
					has_property('interests', is_(none())))

		assert_that(prof,
					verifiably_provides(interfaces.IProfessionalProfile))
		assert_that(prof,
					has_property('positions', is_(none())))

		# We can get to the principal representing the user
		assert_that(IPrincipal(prof), has_property('id', user.username))

		with assert_raises(interfaces.EmailAddressInvalid):
			prof.email = u"foo"

		prof.email = 'foo@bar.com'

		prof2 = interfaces.ICompleteUserProfile(user)
		assert_that(prof2.email, is_('foo@bar.com'))
		assert_that(prof,
					verifiably_provides(interfaces.ICompleteUserProfile))

		# Because of inheritance, even if we ask for IFriendlyNamed, we get ICompleteUserProfile
		prof2 = interfaces.IFriendlyNamed(user)
		assert_that(prof2.email, is_('foo@bar.com'))
		assert_that(prof,
					verifiably_provides(interfaces.ICompleteUserProfile))

		# We can get to the email address
		assert_that(interfaces.IEmailAddressable(user), has_property('email', 'foo@bar.com'))

	def test_non_blank_fields(self):
		user = User(username="foo@bar")

		prof = interfaces.ICompleteUserProfile(user)

		for field in ('affiliation', 'role', 'location', 'description'):
			with assert_raises(interfaces.FieldCannotBeOnlyWhitespace):
				setattr(prof, field, '   ')  # spaces
			with assert_raises(interfaces.FieldCannotBeOnlyWhitespace):
				setattr(prof, field, '\t')  # tab

			setattr(prof, field, '  \t bc')

	def test_updating_realname_from_external(self):
		user = User(username="foo@bar")

		user.updateFromExternalObject({'realname': 'Foo Bar' })

		prof = interfaces.ICompleteUserProfile(user)
		assert_that(prof,
					has_property('realname', 'Foo Bar'))

		interface.alsoProvides(user, interfaces.IImmutableFriendlyNamed)
		user.updateFromExternalObject({'realname': 'Changed Name' })

		prof = interfaces.ICompleteUserProfile(user)
		assert_that(prof,
					has_property('realname', 'Foo Bar'))

	def test_updating_avatar_url_from_external(self):
		user = User(username="foo@bar")

		user.updateFromExternalObject({'avatarURL': 'http://localhost/avatarurl' })

		prof = interfaces.ICompleteUserProfile(user)
		assert_that(prof,
					has_property('avatarURL', 'http://localhost/avatarurl'))

	def test_user_profile_with_legacy_dict(self):
		user = User("foo@bar")
		user._alias = 'bizbaz'
		user._realname = 'boo'

		prof = interfaces.ICompleteUserProfile(user)
		assert_that(prof, verifiably_provides(interfaces.ICompleteUserProfile))

		assert_that(prof, has_property('alias', 'bizbaz'))
		assert_that(prof, has_property('realname', 'boo'))

		prof.alias = 'haha'
		prof.realname = 'hehe'

		assert_that(prof, has_property('alias', 'haha'))
		assert_that(prof, has_property('realname', 'hehe'))

		assert_that(user.__dict__, does_not(has_key('_alias')))
		assert_that(user.__dict__, does_not(has_key('_realname')))

	def test_everyone_names(self):
		everyone = Everyone()
		names = interfaces.IFriendlyNamed(everyone)
		assert_that(names, has_property('alias', 'Public'))
		assert_that(names, has_property('realname', 'Everyone'))

	@mock_dataserver.WithMockDSTrans
	def test_externalizing_extended_fields(self):
		user = User.create_user(username="foo@bar")

		ext_user = to_external_object(user)
		assert_that(ext_user, has_entry('location', None))

		prof = interfaces.ICompleteUserProfile(user)
		prof.location = 'foo bar'

		ext_user = to_external_object(user)
		assert_that(ext_user, has_entry('location', 'foo bar'))

	@mock_dataserver.WithMockDSTrans
	def test_externalized_profile(self):
		user = User.create_user(username="foo@bar")
		prof = interfaces.ICompleteUserProfile(user)
		ext_prof = to_external_object( user, name=('personal-summary') )
		assert_that( ext_prof, has_entry( 'positions', none() ))
		assert_that( ext_prof, has_entry( 'education', none() ))

		# Add position/education
		start_year = 1999
		end_year = 2004
		company_name = 'Omnicorp'
		title = 'Ex VP'
		description = 'ima description'
		school = 'School of Hard Knocks'
		degree = 'CS'
		
		prof.interests = ['reading', 'development']
		
		prof.positions = [ProfessionalPosition( startYear=start_year,
												endYear=end_year,
												companyName=company_name,
												title=title,
												description=description )]
		prof.education = [Education(startYear=start_year,
									endYear=end_year,
									school=school,
									degree=degree,
									description=description )]
		user_prof = to_external_object( user, name=('personal-summary') )

		ext_prof = user_prof.get( 'interests' )
		assert_that( ext_prof, has_length( 2 ))
		
		# Positions
		ext_prof = user_prof.get( 'positions' )
		assert_that( ext_prof, has_length( 1 ))

		ext_prof = ext_prof[0]
		# Clear optional field
		ext_prof[ 'endYear' ] = ''
		assert_that(ext_prof, has_entry('Class',
										ProfessionalPosition.__external_class_name__ ))
		assert_that(ext_prof, has_entry('MimeType',
										ProfessionalPosition.mime_type ))

		factory = internalization.find_factory_for(ext_prof)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_prof)
		assert_that(new_io, has_property( 'startYear', is_( start_year )))
		assert_that(new_io, has_property( 'endYear', none()))
		assert_that(new_io, has_property( 'companyName', is_( company_name )))
		assert_that(new_io, has_property( 'title', is_( title )))
		assert_that(new_io, has_property( 'description', is_( description )))
		assert_that( new_io, is_( ProfessionalPosition ) )

		# Education
		ext_prof = user_prof.get( 'education' )
		assert_that( ext_prof, has_length( 1 ))

		ext_prof = ext_prof[0]
		assert_that(ext_prof, has_entry('Class',
										Education.__external_class_name__ ))
		assert_that(ext_prof, has_entry('MimeType',
										Education.mime_type ))

		factory = internalization.find_factory_for(ext_prof)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_prof)
		assert_that(new_io, has_property( 'startYear', is_( start_year )))
		assert_that(new_io, has_property( 'endYear', is_( end_year )))
		assert_that(new_io, has_property( 'school', is_( school )))
		assert_that(new_io, has_property( 'degree', is_( degree )))
		assert_that(new_io, has_property( 'description', is_( description )))
		assert_that( new_io, is_( Education ) )

from nti.dataserver.users.user_profile import FriendlyNamed

class TestFriendlyNamed(unittest.TestCase):

	def test_di_lu(self):
		fn = FriendlyNamed(self)
		fn.realname = 'Di Lu'

		assert_that(fn.get_searchable_realname_parts(),
					 is_(('Di', 'Lu')))

	def test_cfa(self):
		fn = FriendlyNamed(self)
		fn.realname = "Jason Madden, CFA"
		assert_that(fn.get_searchable_realname_parts(),
					 is_(('Jason', 'Madden')))
