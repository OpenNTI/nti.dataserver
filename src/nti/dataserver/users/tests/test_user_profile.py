#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

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
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import contains_string
does_not = is_not

from nti.testing.matchers import is_false
from nti.testing.matchers import verifiably_provides

import unittest

from zope import interface

from zope.security.interfaces import IPrincipal

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users import interfaces

from nti.dataserver.users.communities import Everyone

from nti.dataserver.users.users import User

from nti.dataserver.users.user_profile import Address
from nti.dataserver.users.user_profile import Education
from nti.dataserver.users.user_profile import ProfessionalPosition

from nti.externalization import internalization

from nti.externalization.externalization import to_external_object


class TestUserProfile(DataserverLayerTest):

    def test_email_address_invalid_domain(self):
        with self.assertRaises(interfaces.EmailAddressInvalid):
            interfaces._checkEmailAddress('poop@poop.poop')  # real-world example

        interfaces._checkEmailAddress('poop@poop.poop.com')
        interfaces._checkEmailAddress('poop@poop.poop.co')

    def test_default_user_profile(self):
        user = User(username=u"foo@bar")

        prof = interfaces.ICompleteUserProfile(user)
        assert_that(prof,
                    verifiably_provides(interfaces.ICompleteUserProfile))
        assert_that(prof,
                    has_property('avatarURL', contains_string('https://')))
        assert_that(prof,
                    has_property('backgroundURL', is_(none())))
        assert_that(prof,
                    has_property('opt_in_email_communication', is_false()))

        assert_that(prof,
                    verifiably_provides(interfaces.ISocialMediaProfile))

        assert_that(prof,
                    verifiably_provides(interfaces.IUserContactProfile))

        assert_that(prof,
                    has_property('twitter', is_(none())))

        assert_that(prof,
                    has_property('facebook', is_(none())))

        assert_that(prof,
                    has_property('instagram', is_(none())))

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

        with self.assertRaises(interfaces.EmailAddressInvalid):
            prof.email = u"foo"

        prof.email = u'foo@bar.com'

        prof2 = interfaces.ICompleteUserProfile(user)
        assert_that(prof2.email, is_('foo@bar.com'))
        assert_that(prof,
                    verifiably_provides(interfaces.ICompleteUserProfile))

        # Because of inheritance, even if we ask for IFriendlyNamed, we get
        # ICompleteUserProfile
        prof2 = interfaces.IFriendlyNamed(user)
        assert_that(prof2.email, is_('foo@bar.com'))
        assert_that(prof,
                    verifiably_provides(interfaces.ICompleteUserProfile))

        # We can get to the email address
        assert_that(interfaces.IEmailAddressable(user),
                    has_property('email', 'foo@bar.com'))

    def test_non_blank_fields(self):
        user = User(username=u"foo@bar")

        prof = interfaces.ICompleteUserProfile(user)

        for field in ('affiliation', 'role', 'location', 'description'):
            with self.assertRaises(interfaces.FieldCannotBeOnlyWhitespace):
                setattr(prof, field, u'   ')  # spaces
            with self.assertRaises(interfaces.FieldCannotBeOnlyWhitespace):
                setattr(prof, field, u'\t')  # tab

            setattr(prof, field, u'  \t bc')

    def test_updating_realname_from_external(self):
        user = User(username=u"foo@bar")

        user.updateFromExternalObject({'realname': u'Foo Bar'})

        prof = interfaces.ICompleteUserProfile(user)
        assert_that(prof,
                    has_property('realname', 'Foo Bar'))

        interface.alsoProvides(user, interfaces.IImmutableFriendlyNamed)
        user.updateFromExternalObject({'realname': u'Changed Name'})

        prof = interfaces.ICompleteUserProfile(user)
        assert_that(prof,
                    has_property('realname', 'Foo Bar'))

    def test_updating_avatar_url_from_external(self):
        user = User(username=u"foo@bar")

        user.updateFromExternalObject({
            'avatarURL': u'http://localhost/avatarurl'
        })

        prof = interfaces.ICompleteUserProfile(user)
        assert_that(prof,
                    has_property('avatarURL', 'http://localhost/avatarurl'))

    def test_user_profile_with_legacy_dict(self):
        user = User(u"foo@bar")
        user._alias = u'bizbaz'
        user._realname = u'boo'

        prof = interfaces.ICompleteUserProfile(user)
        assert_that(prof, verifiably_provides(interfaces.ICompleteUserProfile))

        assert_that(prof, has_property('alias', 'bizbaz'))
        assert_that(prof, has_property('realname', 'boo'))

        prof.alias = u'haha'
        prof.realname = u'hehe'

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
        user = User.create_user(username=u"foo@bar")

        ext_user = to_external_object(user)
        assert_that(ext_user, has_entry('location', None))

        prof = interfaces.ICompleteUserProfile(user)
        prof.location = u'foo bar'

        ext_user = to_external_object(user)
        assert_that(ext_user, has_entry('location', 'foo bar'))

    @mock_dataserver.WithMockDSTrans
    def test_externalized_profile(self):
        user = User.create_user(username=u"foo@bar")
        prof = interfaces.ICompleteUserProfile(user)
        ext_prof = to_external_object(user, name=('personal-summary'))
        assert_that(ext_prof, has_entry('positions', none()))
        assert_that(ext_prof, has_entry('education', none()))

        # Add position/education
        start_year = 1999
        end_year = 2004
        company_name = u'Omnicorp'
        title = u'Ex VP'
        description = u'uima description'
        school = u'School of Hard Knocks'
        degree = u'CS'

        prof.interests = [u'reading', u'development']

        prof.positions = [ProfessionalPosition(startYear=start_year,
                                               endYear=end_year,
                                               companyName=company_name,
                                               title=title,
                                               description=description)]
        prof.education = [Education(startYear=start_year,
                                    endYear=end_year,
                                    school=school,
                                    degree=degree,
                                    description=description)]
        user_prof = to_external_object(user, name=('personal-summary'))

        ext_prof = user_prof.get('interests')
        assert_that(ext_prof, has_length(2))

        # Positions
        ext_prof = user_prof.get('positions')
        assert_that(ext_prof, has_length(1))

        ext_prof = ext_prof[0]
        # Clear optional field
        ext_prof['endYear'] = u''
        assert_that(ext_prof, has_entry('Class',
                                        ProfessionalPosition.__external_class_name__))
        assert_that(ext_prof, has_entry('MimeType',
                                        ProfessionalPosition.mime_type))

        # add contact info
        mailing_address = Address()
        mailing_address.city = u'Karakura Town'
        mailing_address.country = u'Japan'
        mailing_address.state = u'Chiyoda'
        mailing_address.full_name = u'Kurosaki Ichigo'
        mailing_address.street_address_1 = u'Kurosaki Clinic'
        mailing_address.street_address_2 = u'クロサキ医院'
        mailing_address.postal_code = u'100-0001'

        prof.mailing_address = mailing_address
        user_prof = to_external_object(user, name=('personal-summary'))
        
        assert_that(user_prof, 
                    has_entry('mailing_address', has_entries('MimeType', 'application/vnd.nextthought.users.address',
                                                             'city', 'Karakura Town',
                                                             'country', 'Japan',
                                                             'state', 'Chiyoda',
                                                             'postal_code', '100-0001',
                                                             'full_name', 'Kurosaki Ichigo',
                                                             'street_address_1', 'Kurosaki Clinic',)))
        factory = internalization.find_factory_for(ext_prof)
        assert_that(factory, is_(not_none()))

        new_io = factory()
        internalization.update_from_external_object(new_io, ext_prof)
        assert_that(new_io, has_property('startYear', is_(start_year)))
        assert_that(new_io, has_property('endYear', none()))
        assert_that(new_io, has_property('companyName', is_(company_name)))
        assert_that(new_io, has_property('title', is_(title)))
        assert_that(new_io, has_property('description', is_(description)))
        assert_that(new_io, is_(ProfessionalPosition))

        # Education
        ext_prof = user_prof.get('education')
        assert_that(ext_prof, has_length(1))

        ext_prof = ext_prof[0]
        assert_that(ext_prof, has_entry('Class',
                                        Education.__external_class_name__))
        assert_that(ext_prof, has_entry('MimeType',
                                        Education.mime_type))

        factory = internalization.find_factory_for(ext_prof)
        assert_that(factory, is_(not_none()))

        new_io = factory()
        internalization.update_from_external_object(new_io, ext_prof)
        assert_that(new_io, has_property('startYear', is_(start_year)))
        assert_that(new_io, has_property('endYear', is_(end_year)))
        assert_that(new_io, has_property('school', is_(school)))
        assert_that(new_io, has_property('degree', is_(degree)))
        assert_that(new_io, has_property('description', is_(description)))
        assert_that(new_io, is_(Education))
        
        # mailing address
        ext_prof = user_prof.get('mailing_address')
        factory = internalization.find_factory_for(ext_prof)
        assert_that(factory, is_(not_none()))
        
        new_io = factory()
        internalization.update_from_external_object(new_io, ext_prof)
        assert_that(new_io, has_property('city', 'Karakura Town'))
        assert_that(new_io, has_property('country', is_('Japan')))
        assert_that(new_io, has_property('street_address_2', is_(u'クロサキ医院')))
        assert_that(new_io, is_(Address))


from nti.dataserver.users.user_profile import FriendlyNamed


class TestFriendlyNamed(unittest.TestCase):

    def test_di_lu(self):
        fn = FriendlyNamed(self)
        fn.realname = u'Di Lu'

        assert_that(fn.get_searchable_realname_parts(),
                    is_(('Di', 'Lu')))

    def test_cfa(self):
        fn = FriendlyNamed(self)
        fn.realname = u"Jason Madden, CFA"
        assert_that(fn.get_searchable_realname_parts(),
                    is_(('Jason', 'Madden')))
