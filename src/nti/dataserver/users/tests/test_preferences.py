#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property

import nti.tests

setUpModule = lambda: nti.tests.module_setup(set_up_packages=('nti.dataserver',))
tearDownModule = nti.tests.module_teardown

from nti.dataserver.users import User
from nti.dataserver.users import interfaces as user_interfaces

def test_adapter():
	user = User( 'foo@bar' )
	pref = user_interfaces.IEntityPreferences(user, None)
	assert_that(pref, is_not(none()))
	assert_that(pref, has_property('username', is_('foo@bar')))
