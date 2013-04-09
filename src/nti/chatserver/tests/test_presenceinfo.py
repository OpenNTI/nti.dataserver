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
from hamcrest import is_not
from hamcrest import none
from hamcrest import has_item
from hamcrest import has_entries

import nti.tests
from nti.tests import verifiably_provides
from nti.tests import validly_provides
from nose.tools import assert_raises

from zope.schema.interfaces import TooLong

from .. import presenceinfo
from ..interfaces import IPresenceInfo

from nti.externalization import internalization
from nti.externalization.externalization import toExternalObject

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.chatserver','nti.mimetype','nti.contentfragments') )
tearDownModule = nti.tests.module_teardown

def test_implements():

	info = presenceinfo.PresenceInfo()
	assert_that( info, verifiably_provides( IPresenceInfo ) )


	assert_that( info, validly_provides( IPresenceInfo ) )

	with assert_raises(TooLong):
		info.status = 'foo' * 140 # too big

from nti.externalization.tests import externalizes
def test_externalizes():
	info = presenceinfo.PresenceInfo()
	assert_that( info, externalizes( has_entries( 'show', 'chat', 'status', '', 'type', 'available',
												  'Class', 'PresenceInfo', 'MimeType', 'application/vnd.nextthought.presenceinfo') ) )

	factory = internalization.find_factory_for( toExternalObject( info ) )
	assert_that( factory,
				 is_not( none() ) )
	assert_that( list(factory.getInterfaces()),
				 has_item( IPresenceInfo ) )


	internalization.update_from_external_object( info, {'status': 'My status'} )
	assert_that( info.status, is_( 'My status' ) )
	assert_that( info, validly_provides( IPresenceInfo ) )
