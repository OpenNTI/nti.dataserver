#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_property
from hamcrest import is_not
from hamcrest import none

from zope import component
from zope import interface
from zope.keyreference.interfaces import IKeyReference

import nti.tests
from nti.tests import verifiably_provides

from .. import interfaces
from .. import utility
from .. import invitation
from nti.dataserver.generations.install import install_intids

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.dataserver',) )
tearDownModule = nti.tests.module_teardown

def test_valid_interface():

	assert_that( utility.PersistentInvitations(), verifiably_provides( interfaces.IInvitations ) )


def test_add_invitation():

	invites = utility.PersistentInvitations()
	invite = invitation.PersistentInvitation()
	invite.code = 'my code'

	invites.registerInvitation( invite )
	assert_that( invite, has_property( 'code', 'my code' ) )

	assert_that( invites.getInvitationByCode( 'my code' ), is_( invite ) )

	install_intids( component )


	invite = invitation.PersistentInvitation()
	interface.alsoProvides( invite, IKeyReference )

	invites.registerInvitation( invite )
	assert_that( invite, has_property( 'code', is_not( none() ) ) )

	assert_that( invites.getInvitationByCode( invite.code ), is_( invite ) )

	for x in invites.sublocations():
		assert_that( x, has_property( '__parent__', invites ) )
