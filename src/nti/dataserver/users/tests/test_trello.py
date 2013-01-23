from __future__ import print_function, unicode_literals, absolute_import

import unittest

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.dataserver.users import DynamicFriendsList

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase

from hamcrest import (assert_that, is_in)
	
class TestTrello(ConfiguringTestBase):

	@WithMockDS(with_changes=True)
	def test_847(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self.ds.add_change_listener( users.onChange )
			jmadden = users.User.create_user( username='jmadden@nextthought.com' )
			sjohnson = users.User.create_user( username='sjohnson@nextthought.com' )
			
			ntusrs = DynamicFriendsList(username='ntusrs')
			ntusrs.creator = jmadden	
			jmadden.addContainedObject( ntusrs )
			ntusrs.addFriend( sjohnson )
						
			note = Note()
			note.body = [u'Violent Blades']
			note.creator = jmadden.username
			note.containerId = u'c1'
			
			with jmadden.updates():
				note.addSharingTarget( ntusrs )
				note = jmadden.addContainedObject( note )
			
			scnt = sjohnson.getSharedContainer(  u'c1' ) 
			assert_that(note, is_in(scnt))
			
			with jmadden.updates():
				note = jmadden.getContainedObject(u'c1', note.id)
				note.clearSharingTargets()
				note.addSharingTarget( sjohnson )
			
			scnt = sjohnson.getSharedContainer(  u'c1' ) 
			assert_that(note, is_in(scnt))
			
		
if __name__ == '__main__':
	unittest.main()