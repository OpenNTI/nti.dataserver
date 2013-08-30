#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property

from nti.externalization.externalization import to_external_object

import nti.tests

from nti.dataserver.tests import mock_dataserver

setUpModule = lambda: nti.tests.module_setup(set_up_packages=('nti.dataserver', 'nti.dataserver.users',))
tearDownModule = nti.tests.module_teardown

from nti.dataserver.users import User
from nti.dataserver.users import interfaces as user_interfaces

def test_adapter():
	user = User('foo@bar')
	pref = user_interfaces.IEntityPreferences(user, None)
	assert_that(pref, is_not(none()))
	assert_that(pref, has_property('username', is_('foo@bar')))

@mock_dataserver.WithMockDSTrans
def test_decorator():
	user = User.create_user(username="foo@bar")
	pref = user_interfaces.IEntityPreferences(user)
	pref['foo'] = 'bar'
	ext_user = to_external_object(user)
	assert_that(ext_user, has_entry('Preferences', has_entry('foo', 'bar')))
