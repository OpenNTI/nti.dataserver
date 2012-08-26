#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import assert_that
from hamcrest import has_entry


import nti.tests


setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver',) )
tearDownModule = nti.tests.module_teardown

from zope import interface
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces
from nti.dataserver.users import FriendsList
import nti.externalization.internalization
import nti.externalization.externalization


def test_update_friends_list_name():
	class O(object):
		username = 'foo'
		_avatarURL = 'BAD'

	o = FriendsList('MyList')
	ext_value = nti.externalization.externalization.to_external_object( o )
	assert_that( ext_value, has_entry( 'Username', 'MyList' ) )
	assert_that( ext_value, has_entry( 'alias', 'MyList' ) )
	assert_that( ext_value, has_entry( 'realname', 'MyList' ) )

	nti.externalization.internalization.update_from_external_object( o, {'realname': "My Funny Name"} )

	ext_value = nti.externalization.externalization.to_external_object( o )

	assert_that( ext_value, has_entry( 'Username', 'MyList' ) )
	assert_that( ext_value, has_entry( 'realname', 'My Funny Name' ) )
	assert_that( ext_value, has_entry( 'alias', 'My Funny Name' ) )
