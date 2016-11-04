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
from hamcrest import has_length
from hamcrest import has_entries


from nti.testing.matchers import validly_provides as verifiably_provides



from nti.dataserver.contenttypes import Canvas

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object


import nti.dataserver.interfaces as interfaces
nti_interfaces = interfaces

from nti.chatserver import messageinfo
from nti.chatserver import interfaces as chat_interfaces


from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

class TestMessageInfo(DataserverLayerTest):


	def test_interfaces( self ):
		m = messageinfo.MessageInfo()
		assert_that( m, verifiably_provides( nti_interfaces.IModeledContent ) )
		m.sharedWith = set()
		m.creator = ''
		m.__name__ = ''
		m.body = 'foo'
		assert_that( m, verifiably_provides( chat_interfaces.IMessageInfo ) )

	@WithMockDSTrans
	def test_external_body( self ):
		m = messageinfo.MessageInfo()
		assert_that( m, verifiably_provides( nti_interfaces.IModeledContent ) )
		m.Body = 'foo'
		m.Creator = 'Jason'
		assert_that( m, verifiably_provides( chat_interfaces.IMessageInfo ) )
		ext = to_external_object( m )
		assert_that( ext['Body'], is_( ext['body'] ) )

		c = Canvas()
		m.Body = ['foo', c]
		assert_that( m.Body, is_( ['foo', c] ) )
		ext = to_external_object( m )
		assert_that( ext['Body'], has_length( 2 ) )
		assert_that( ext['Body'][0], is_('foo' ) )
		assert_that( ext['Body'][1], has_entries( 'Class', 'Canvas', 'shapeList', [], 'CreatedTime', c.createdTime ) )

		m = messageinfo.MessageInfo()
		update_from_external_object( m, ext, context=self.ds )
		assert_that( m.Body[0], is_( 'foo' ) )
		assert_that( m.Body[1], is_( Canvas ) )

	def test_update_when_legacy_data_in_creator( self ):
		m = messageinfo.MessageInfo()
		assert_that( m, verifiably_provides( nti_interfaces.IModeledContent ) )
		m.Body = 'foo'
		m.Creator = 'Jason'
		assert_that( m, verifiably_provides( chat_interfaces.IMessageInfo ) )

		# Now force the creator to be bytes, bypassing any field conversions
		# as might happen in legacy data
		m.__dict__['Creator'] = b'Jason'
		assert_that( m.Creator, is_( str ) )
		assert_that( m.creator, is_( str ) )
		assert_that( m.Sender, is_( str ) )

		# Now update and it doesn't blow up
		update_from_external_object( m, {} )

	@WithMockDSTrans
	def test_update_when_legacy_data_in_sharedWith( self ):
		m = messageinfo.MessageInfo()
		assert_that( m, verifiably_provides( nti_interfaces.IModeledContent ) )
		m.Body = 'foo'
		m.Creator = 'Jason'
		assert_that( m, verifiably_provides( chat_interfaces.IMessageInfo ) )

		# Now force the creator to be bytes, bypassing any field conversions
		# as might happen in legacy data
		data = {b'Foo', b'Bar', 'baz'}
		m.__dict__['sharedWith'] = data
		assert_that( m.sharedWith, is_( data ) )
		# Now update and it doesn't blow up
		update_from_external_object( m, {} )
