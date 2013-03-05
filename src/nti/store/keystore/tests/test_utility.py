#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904 access

from .. import utility
from .. import access_key

from ...tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_property)

class TestUtility(ConfiguringTestBase):
	
	def test_add_key(self):

		keystore = utility.PersistentKeyStore()
		pk = access_key.PersistentAccessKey('mykey', '1234')
	
		keystore.registerKey( pk )
		assert_that( pk, has_property( 'value', '1234' ) )
		assert_that( pk, has_property( 'alias', 'mykey') )
	
		assert_that( keystore.getKeyByAlias('mykey'), is_( pk ) )
	
		for x in keystore.sublocations():
			assert_that( x, has_property( '__parent__', keystore ) )


		
