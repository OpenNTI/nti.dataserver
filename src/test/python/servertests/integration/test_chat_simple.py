import time
import random
import threading

from user_chat_objects import OneRoomUser
from user_chat_objects import BasicChatTest

class TestSimpleChat(BasicChatTest):
	
	def setUp(self):
		super(TestSimpleChat, self).setUp()
		self.user_one = self.user_names[0]
		self.user_two = self.user_names[1]
	
	def test_chat(self):
		entries = random.randint(5, 10)
		one, two = run_chat(entries, self.user_one, self.user_two)
		
		for u in (one,two):
			self.assert_(u.exception == None, "User %s caught exception %s" % (u.username, u.exception))
			
		self._compare(one, two)
		self._compare(two, one)
		
	def _compare(self, sender, receiver):
		
		_sent = list(sender.sent)
		self.assertTrue(len(_sent) > 0, "%s did not send any messages" % sender)
		_sent.sort()
		
		_recv = list(receiver.received)
		self.assertTrue(len(_recv) > 0, "%s did not get any messages" % receiver)
		_recv.sort()
		
		self.assertEqual(_sent, _recv, "%s did not get all messages from %s" % (receiver, sender))
		
# ----------------------------

def run_chat(entries, user_one, user_two):
	
	connect_event = threading.Event()
	one = User(username=user_one)
	two = User(username=user_two)
		
	print "entries", entries
	
	def two_runnable():
		t_args={'occupants':(user_one), 'entries':entries}
		try:
			time.sleep(1)
			two.ws_connect()
			connect_event.set()
			two(**t_args)
		except Exception, e:
			two.exception = e
			two.ws_capture_and_close()
	
	o_args={'entries':entries, 'connect_event':connect_event}
	o_t=threading.Thread(target=one, kwargs=o_args)
	o_t.start()

	t_t=threading.Thread(target=two_runnable)
	t_t.start()

	for t in (o_t, t_t):
		t.join()
		
	return one, two
			
# ----------------------------

class User(OneRoomUser):
		
	def __call__(self, *args, **kwargs):
		t = time.time()
		try:
			entries = kwargs.get('entries', None)
			occupants = kwargs.get('occupants', None)
					
			# connect
			if not self.ws_connected:
				self.ws_connect()
	
			# check for an connect event
			event = kwargs.get('connect_event', None)
			if event: 
				event.wait(60)
					
			if occupants:
				self.enterRoom(occupants)
				
			self.wait_4_room()
				
			# write any messages
			room_id = self.room
			if room_id:
				self.post_random_messages(room_id, entries, 5)
					
			# get any message
			self.wait_heart_beats()
					
		except Exception, e:
			self.exception = e
		finally:
			self.ws_capture_and_close()
			print "exit %s,%s" % (self, time.time() - t)
	
if __name__ == '__main__':
	import unittest
	unittest.main()
	