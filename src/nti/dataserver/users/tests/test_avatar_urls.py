#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import has_item
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string
from hamcrest import greater_than_or_equal_to

from zope import interface

from zope.annotation import interfaces as an_interfaces

from nti.dataserver import users
from nti.dataserver.users import Everyone
from nti.dataserver.users import interfaces
from nti.dataserver.users import users_external
from nti.dataserver import interfaces as nti_interfaces

from nti.links import links

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.testing.matchers import verifiably_provides

class TestAvatarURLs(DataserverLayerTest):

	def test_coppa_user(self):
		class O(object):
			username = 'foo'
			_avatarURL = 'BAD'

		o = O()

		interface.alsoProvides(o, nti_interfaces.ICoppaUserWithAgreement)
		interface.alsoProvides(o, an_interfaces.IAttributeAnnotatable)

		assert_that(interfaces.IAvatarURL(o),
					verifiably_provides(interfaces.IAvatarURL))
		assert_that(interfaces.IAvatarURL(o),
					has_property('avatarURL', contains_string('https://')))

		choices = interfaces.IAvatarChoices(o).get_choices()
		assert_that(choices, has_length(greater_than_or_equal_to(16)))
		assert_that(choices, has_item(interfaces.IAvatarURL(o).avatarURL))

		profile = interfaces.IAvatarURL(o)
		profile.avatarURL = 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='
		_file = getattr(type(profile), 'avatarURL').get_file(profile)
		_file.to_external_ntiid_oid = lambda: 'the_external_ntiid'  # rather than setting up _p_jar
		assert_that(users_external._avatar_url(o), is_(links.Link))

		# host-less URLs are ignored
		profile.avatarURL = '/a/path/to/data/@@view'
		assert_that(users_external._avatar_url(o), is_(links.Link))

	def test_user_with_email(self):
		u = users.User("jason.madden@nextthought.com")
		profile = interfaces.ICompleteUserProfile(u)

		profile.email = 'jason.madden@nextthought.com'

		avurl_prof = interfaces.IAvatarURL(u)
		assert_that(avurl_prof.avatarURL,
					is_('https://secure.gravatar.com/avatar/5738739998b683ac8fe23a61c32bb5a0?s=128&d=identicon#using_provided_email_address'))

		avurl_prof = interfaces.IBackgroundURL(u)
		assert_that(avurl_prof.backgroundURL, is_(none()))

	def test_everyone(self):
		o = Everyone()
		assert_that(interfaces.IAvatarURL(o),
					verifiably_provides(interfaces.IAvatarURL))

		assert_that(interfaces.IAvatarURL(o),
					has_property('avatarURL', contains_string('http://')))

		assert_that(interfaces.IBackgroundURL(o),
					has_property('backgroundURL', is_(none())))

		choices = interfaces.IAvatarChoices(o).get_choices()
		assert_that(choices, has_length(1))
		assert_that(choices, has_item(interfaces.IAvatarURL(o).avatarURL))
