import os
import shutil
import tempfile
import unittest

from zope import component
from zope.configuration import xmlconfig

from nti.dataserver.users import User

from nti.externalization.internalization import update_from_external_object

import nti.contentsearch as contentsearch
from nti.contentsearch._whoosh_entity_index import IWhooshEntityIndex

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_redis import InMemoryMockRedis
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

import zope.testing.cleanup

from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_length)

# complement mock redis with pub/sub

def pubsub(self):
	self.__dict__['topics'] = set()
	return self

def subscribe(self, topic):
	self.__dict__['topics'].add(topic)
	self.pipeline().rpush(topic, 'subscribe').execute()
	
def publish(self, topic, msg):
	topics = self.__dict__.get('topics', ())
	if topic in topics:
		self.pipeline().rpush(topic, msg).execute()
	
def unsubscribe(self, topic):
	topics = self.__dict__.get('topics', None)
	if topics:
		topics.discard(topic)

def listen(self):
	topics = self.__dict__.get('topics', ())
	for topic in topics:
		msgs, _ = self.pipeline().lrange(topic, 0, -1).delete(topic).execute()
		for m in msgs:
			yield m
	
class TestWhooshUserIndex(ConfiguringTestBase):		

	@classmethod
	def setUpClass(cls):
		zope.testing.cleanup.cleanUp()
		InMemoryMockRedis.pubsub = pubsub
		InMemoryMockRedis.listen = listen
		InMemoryMockRedis.publish = publish
		InMemoryMockRedis.subscribe = subscribe
		InMemoryMockRedis.unsubscribe = unsubscribe

	@classmethod
	def tearDownClass(cls):
		zope.testing.cleanup.cleanUp()
		del InMemoryMockRedis.pubsub
		del InMemoryMockRedis.listen
		del InMemoryMockRedis.publish
		del InMemoryMockRedis.subscribe
		del InMemoryMockRedis.unsubscribe
	
	def setUp( self ):
		super(TestWhooshUserIndex,self).setUp()
		xmlconfig.file("whoosh_entity_index.zcml", contentsearch, context=self.configuration_context)
		self.db_dir = tempfile.mkdtemp(dir="/tmp")
		os.environ['DATASERVER_DIR']= self.db_dir
		
	def tearDown( self ):
		uidx_util = component.getUtility(IWhooshEntityIndex)
		uidx_util.close()
		shutil.rmtree(self.db_dir, True)
		super(TestWhooshUserIndex, self).tearDown()
		
	def _create_user(self, username='nt@nti.com', password='temp001', external_value={}):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password, external_value=external_value)
		return usr
	
	@WithMockDSTrans
	def test_index_users(self):
		self._create_user()
		uidx_util = component.getUtility(IWhooshEntityIndex)
		assert_that(uidx_util.index, is_not(None))
		assert_that(uidx_util.doc_count(), is_(2))
		# check publish messages (subcribe and creation)
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(2)) 
		
		# add listener should work
		user= self._create_user(username='nt2@nti.com')
		assert_that(uidx_util.doc_count(), is_(3))
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(1))
		
		# check all  msgs have been consumed
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(0))
		
		# modified listener
		external= {u'email':u'foo@bar.com'}
		update_from_external_object(user, external)
		assert_that(uidx_util.doc_count(), is_(3))
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(1))
			
		# delete listener
		User.delete_user('nt2@nti.com')
		assert_that(uidx_util.doc_count(), is_(2))
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(1))

if __name__ == '__main__':
	unittest.main()
