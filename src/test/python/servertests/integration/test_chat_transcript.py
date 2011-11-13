import random

from user_chat_objects import BasicChatTest
from websocket_interface import CouldNotEnterRoom

class TestChatTranscript(BasicChatTest):
		
	def setUp(self):
		super(TestChatTranscript, self).setUp()
		self.user_one = self.user_names[0]
		self.user_two = self.user_names[1]
	
	def test_transcript(self):
		
		from test_chat_simple import run_chat
		
		entries = random.randint(20, 50)
		one, _ = run_chat(entries, self.user_one, self.user_two)
			
		room_id = one.room
		if not room_id:
			raise CouldNotEnterRoom()
		
		all_msgs = []
		map(lambda x: all_msgs.append(x), one.sent)
		map(lambda x: all_msgs.append(x), one.received)
		
		self.ds.setCredentials(user=one.username, passwd=one.password)
		t = self.ds.getTranscripts(room_id)
		
		self.assertTrue(t.has_key(u'RoomInfo'), 'Could not find room info')
		ri = t[u'RoomInfo']
		self.assertEqual(entries*2, ri[u'MessageCount'], 'Unexpected message count')
		self.assertEqual(room_id, ri[ u'ID'], 'Unexpected room id')
		
		self.assertTrue(t.has_key(u'Messages'), 'Incomplete message')
		messages = t['Messages']
		for m in messages:
			body = m['Body']
			self.assert_(body != None, 'Invalid body')
			self.assert_(m[u'ID'], 'No id for message found')
			self.assertEqual(m[u'ContainerId'], room_id, 'Unexpected message room id')
			self.assertEqual(m[u'Status'], u'st_POSTED', 'Unexpected message status')
			self.assert_(body in all_msgs, 'Unexpected message')
		
		
if __name__ == '__main__':
	import unittest
	unittest.main()
	