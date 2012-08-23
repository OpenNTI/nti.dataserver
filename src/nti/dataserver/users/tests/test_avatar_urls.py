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

import nti.tests
from nti.tests import verifiably_provides

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver',) )
tearDownModule = nti.tests.module_teardown

from zope import interface
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces
from nti.dataserver.users import Everyone

def test_coppa_user():
	class O(object):
		username = 'foo'
		_avatarURL = 'BAD'

	o = O()


	interface.alsoProvides( o, nti_interfaces.ICoppaUserWithAgreement )

	assert_that( interfaces.IAvatarURL( o ),
				 verifiably_provides( interfaces.IAvatarURL ) )
	assert_that( interfaces.IAvatarURL( o ),
				 has_property( 'avatarURL', contains_string( 'http://' ) ) )

def test_everyone():

	o = Everyone()

	assert_that( interfaces.IAvatarURL( o ),
				 verifiably_provides( interfaces.IAvatarURL ) )
	assert_that( interfaces.IAvatarURL( o ),
				 has_property( 'avatarURL', contains_string( 'http://' ) ) )
