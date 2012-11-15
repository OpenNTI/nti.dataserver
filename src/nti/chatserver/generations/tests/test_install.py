from __future__ import print_function, unicode_literals

import unittest

from zope import component
from zope.event import notify
from zope.component.hooks import site
from zope.lifecycleevent import ObjectAddedEvent

from zope.catalog.interfaces import ICatalog

from nti.chatserver import meeting 
from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import mock_db_trans

import fudge
from hamcrest import assert_that, is_not, contains

class TestInstall(mock_dataserver.ConfiguringTestBase):

	@mock_dataserver.WithMockDS
	def test_installed_catalog(self):
		
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			with site(ds_folder):
				chat_catalog = component.getUtility(ICatalog, name=chat_interfaces.MEETING_CATALOG_NAME)
				assert_that(chat_catalog, is_not(None))
				
				room = meeting._Meeting( None )
				room.id = 'foo'
				room.__parent__ = ds_folder
				conn.add(room)
				notify(ObjectAddedEvent(room))
	
				results = list(chat_catalog.searchResults( RoomId=('foo','foo')))
				assert_that( results, contains( room ) )
				
if __name__ == '__main__':
	unittest.main()