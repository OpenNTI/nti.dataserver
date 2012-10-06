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
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_property


from nti.tests import verifiably_provides

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


from nti.dataserver import users
from nti.dataserver import intid_wref as wref


import BTrees.OOBTree
import cPickle

class TestWref(ConfiguringTestBase):

	@WithMockDSTrans
	def test_pickle( self ):
		user = users.User.create_user( username='sjohnson@nextthought.com' )

		ref = wref.WeakRef( user )

		assert_that( ref, has_property( '_v_entity_cache', user ) )

		copy = cPickle.loads( cPickle.dumps( ref ) )

		assert_that( copy, has_property( '_v_entity_cache', none() ) )

		assert_that( copy(), is_( user ) )
		assert_that( ref, is_( copy ) )
		assert_that( copy, is_( ref ) )
		assert_that( repr(copy), is_( repr( ref ) ) )
		assert_that( hash(copy), is_( hash( ref ) ) )
		assert_that( ref, verifiably_provides( nti_interfaces.IWeakRef ) )

	@WithMockDSTrans
	def test_missing( self ):
		user = users.User.create_user( username='sjohnson@nextthought.com' )

		ref = wref.WeakRef( user )
		setattr( ref, '_v_entity_cache', None )
		setattr( ref, '_entity_id', -1 )

		assert_that( ref(), is_( none() ) )

		ref = wref.WeakRef( user )
		assert_that( ref, has_property( '_entity_oid', not_none() ) )
		setattr( ref, '_v_entity_cache', None )
		setattr( ref, '_entity_oid', -1 )
		assert_that( ref(), is_( none() ) )

		ref = wref.WeakRef( user )
		assert_that( ref, has_property( '_entity_oid', not_none() ) )
		setattr( ref, '_v_entity_cache', None )
		setattr( ref, '_entity_oid', None )
		assert_that( ref(), is_( user ) )


	@WithMockDSTrans
	def test_in_btree(self):
		user = users.User.create_user( username='sjohnson@nextthought.com' )
		user2 = users.User.create_user( username='sjohnson2@nextthought.com' )

		bt = BTrees.OOBTree.OOBTree()

		ref = wref.WeakRef( user )
		ref2 = wref.WeakRef( user2 )

		bt[ref] = 1
		bt[ref2] = 2

		assert_that( bt[ref], is_( 1 ) )
		assert_that( bt[ref2], is_( 2 ) )

		assert_that( bt.get('foo'), is_( none() ) )
