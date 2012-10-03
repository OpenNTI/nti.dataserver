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
from hamcrest import contains
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

from zope.component import eventtesting

def test_valid_interface():

	assert_that( invitation.PersistentInvitation(), verifiably_provides( interfaces.IInvitation ) )

def test_accept_event():
	eventtesting.clearEvents()
	component.provideHandler( eventtesting.events.append, (None,) )

	invite = invitation.PersistentInvitation()
	invite.accept( invite )

	assert_that( eventtesting.getEvents( interfaces.IInvitationAcceptedEvent ),
				 contains( has_property( 'object', invite ) ) )
