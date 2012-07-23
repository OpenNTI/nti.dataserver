#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authentication

from nti.tests import verifiably_provides
from pyramid.testing import DummySecurityPolicy

def test_delegating_provides():

	assert_that( authentication.DelegatingImpersonatedAuthenticationPolicy( DummySecurityPolicy( '' ) ),
				 verifiably_provides( nti_interfaces.IImpersonatedAuthenticationPolicy ) )

def test_effective_prins_no_username():
	assert_that( authentication.effective_principals( '' ), is_( () ) )
