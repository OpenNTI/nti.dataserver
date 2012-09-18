#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string
from hamcrest import has_length
from hamcrest import is_
from hamcrest import has_item

import nti.tests
from nti.tests import verifiably_provides

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver',) )
tearDownModule = nti.tests.module_teardown

from zope import interface
from zope.annotation import interfaces as an_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import links
from nti.dataserver.users import interfaces
from nti.dataserver.users import Everyone
from nti.dataserver.users import users_external

def test_coppa_user():
	class O(object):
		username = 'foo'
		_avatarURL = 'BAD'

	o = O()


	interface.alsoProvides( o, nti_interfaces.ICoppaUserWithAgreement )
	interface.alsoProvides( o, an_interfaces.IAttributeAnnotatable )

	assert_that( interfaces.IAvatarURL( o ),
				 verifiably_provides( interfaces.IAvatarURL ) )
	assert_that( interfaces.IAvatarURL( o ),
				 has_property( 'avatarURL', contains_string( 'http://' ) ) )

	choices = interfaces.IAvatarChoices( o ).get_choices()
	assert_that( choices, has_length( 8 ) )
	assert_that( choices, has_item( interfaces.IAvatarURL( o ).avatarURL ) )

	profile = interfaces.IAvatarURL( o )
	profile.avatarURL = 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='

	assert_that( users_external._avatar_url( o ), is_( links.Link ) )


def test_everyone():

	o = Everyone()

	assert_that( interfaces.IAvatarURL( o ),
				 verifiably_provides( interfaces.IAvatarURL ) )
	assert_that( interfaces.IAvatarURL( o ),
				 has_property( 'avatarURL', contains_string( 'http://' ) ) )

	choices = interfaces.IAvatarChoices( o ).get_choices()
	assert_that( choices, has_length( 1 ) )
	assert_that( choices, has_item( interfaces.IAvatarURL( o ).avatarURL ) )
