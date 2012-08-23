#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_property
from hamcrest import contains_string

from nose.tools import assert_raises

import nti.tests
from nti.tests import verifiably_provides

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver',) )
tearDownModule = nti.tests.module_teardown

from zope import interface
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces
from nti.dataserver.users import Everyone
from nti.dataserver.users import User

def test_default_user():
	user = User( username="foo@bar" )

	prof = interfaces.ICompleteUserProfile( user )
	assert_that( prof,
				 verifiably_provides( interfaces.ICompleteUserProfile ) )
	assert_that( prof,
				 has_property( 'avatarURL', contains_string( 'http://' ) ) )


	with assert_raises(interfaces.EmailAddressInvalid):
		prof.email = u"foo"

	prof.email = 'foo@bar.com'

	prof2 = interfaces.ICompleteUserProfile( user )
	assert_that( prof2.email, is_( 'foo@bar.com' ) )
	assert_that( prof,
				 verifiably_provides( interfaces.ICompleteUserProfile ) )
