'''
Created on Nov 18, 2011

@author: ltesti
'''
import time
import threading

from user_chat_objects import OneRoomUser
from user_chat_objects import BasicChatTest

class TestSimpleChat(BasicChatTest):
	
	def setUp(self):
		super(TestSimpleChat, self).setUp()
		self.user_one = self.user_names[0]
		self.user_two = self.user_names[1]
		self.user_three = self.user_names[2]
		self.register_friends(self.user_three, [self.user_one, self.user_two])
		self.user_four = self.user_names[3]
		self.register_friends(self.user_four, str((self.user_one, self.user_two)))
		self.user_five = self.generate_user_name()
	
	def test_chat_user_leaves_early(self):
		one, two = run_chat(self.user_one, self.user_two, LeavesEarly=True)
		
		for u in (one,two):
			self.assert_(u.exception == None, "User %s caught exception %s" % (u.username, u.exception))
			
		self._compare(one, two, receivedAllMessages=False)
		self._compare(two, one)
		
	def _compare(self, sender, receiver, receivedAllMessages=True):
		
		_sent = list(sender.sent)
		self.assertTrue(len(_sent) > 0, "%s did not send any messages" % sender)
		_sent.sort()
		
		_recv = list(receiver.received)
		self.assertTrue(len(_recv) > 0, "%s did not get any messages" % receiver)
		_recv.sort()
		
		if receivedAllMessages == True: self.assertEqual(_sent, _recv, "%s did not get all messages from %s" % (receiver, sender))
		else: self.assertNotEqual(_sent, _recv, "%s did not get all messages from %s" % (receiver, sender))
		
# ----------------------------

def run_chat(user_one, user_two, LeavesEarly=False):
	entries = 2
	connect_event = threading.Event()
	one = User(username=user_one)
	two = User(username=user_two, LeavesEarly=LeavesEarly)
	
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
		
	def __init__(self, LeavesEarly=False, **kwargs):
		super(User, self).__init__(**kwargs)
		self.LeavesEarly=LeavesEarly
		
	def __call__(self, *args, **kwargs):
		self.t = time.time()
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
				self.post_random_messages(room_id, entries)
				print 'messages posted by %s' % self.username
			
			# get any message
			self.wait_heart_beats(1)
			
			if self.username == 'test.user.2@nextthought.com' and self.LeavesEarly == True:
				self.userLeaves()
				return
			#get any message
			self.wait_heart_beats(1)
			
			if room_id:
				self.post_random_messages(room_id, entries)
				print 'messages posted by %s' % self.username
					
			# get any message
			self.wait_heart_beats(2)
			
			self.userLeaves()

		except Exception, e:
			self.exception = e
			
	def userLeaves(self):
		self.ws_capture_and_close()
		print "exit %s,%s" % (self, time.time() - self.t)
	
if __name__ == '__main__':
	import unittest
	unittest.main()