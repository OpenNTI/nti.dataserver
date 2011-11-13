import time
import random
import threading

from user_chat_objects import OneRoomUser
from user_chat_objects import BasicChatTest

class TestModeratedChat(BasicChatTest):
	
	def setUp(self):
		super(TestModeratedChat, self).setUp()	
		self.users = self.user_names[:3]
	
	def _launch(self, threads, user, args):
		t=threading.Thread(target=user, kwargs=args)
		threads[user] = t 
		t.start()
		return t
		
	def test_chat(self):
		connect_event = threading.Event()
		
		occupants = self.users[1:]
		moderator = Moderator(username=self.users[0], occupants=occupants)
		chatters = [User(username=u) for u in occupants]
	
		threads = {}
		args={'connect_event':connect_event}
		self._launch(threads, moderator, args)
		
		# wait till moderador connects
		time.sleep(1.0)
		
		# start chatters
		entries = random.randint(5, 10)
		print "entries", entries
		
		for user in chatters:
			args={'entries':entries, 'connect_event':connect_event}
			self._launch(threads, user, args)
			
		for t in threads.itervalues():
			t.join()
			
		# ------ do checks ------
		
		for u in threads.iterkeys():
			self.assert_(u.exception == None, "User %s exception %s" % (u.username, u.exception))
		
		all_recv=set()
		for c in chatters:
			msgs = c.recv_messages
			self.assert_(len(msgs)>0, "User %s did not get any message" % c.username)
			map(lambda x: all_recv.add(x), msgs.iterkeys())
		
		for m in all_recv:
			self.assert_(m not in moderator.moderated_messages, "Moderated message %s was received by a user" % m)
		
# ----------------------------

class User(OneRoomUser):
		
	def __call__(self, connect_event, entries=None):
		t = time.time()
		try:
			self.ws_connect()
			connect_event.wait(60)
					
			# wait for a room
			self.wait_4_room()		
	
			# write any messages
			self.post_random_messages(self.room, entries)
					
			# get any message
			self.wait_heart_beats()
					
		except Exception, e:
			self.exception = e
		finally:
			self.ws_capture_and_close()
			print "exit %s,%s" % (self, time.time() - t)
			
class Moderator(User):
		
	def __init__(self, username, occupants):
		super(Moderator, self).__init__(username=username)
		self.occupants = occupants
		self.online = set()
		
	def chat_recvMessageForModeration(self, **kwargs):
		super(Moderator, self).chat_recvMessageForModeration(**kwargs)
		self.heart_beats = 0
		mid = kwargs['ID']
		if random.random() > 0.7:
			self.approveMessages(mid)
			self.moderated_messages.pop(mid , None)
	
	def chat_presenceOfUserChangedTo(self, username, status):
		if status == 'Online' and username in self.occupants:
			self.online.add(username)
			self.heart_beats = 0
		
	def __call__(self, connect_event):
		t = time.time()
		try:
			self.ws_connect()
			
			# wait users are connected
			
			self.heart_beats = 0
			while self.heart_beats < 5 and len(self.online) < len(self.occupants):
				self.nextEvent()				
				
			self.enterRoom(self.occupants)
			self.wait_4_room()	
			self.makeModerated(self.room)		
			connect_event.set()	
			
			# process messages
			self.wait_heart_beats()
					
		except Exception, e:
			self.exception = e
		finally:
			self.ws_capture_and_close()
			print "exit %s,%s" % (self, time.time() - t)
	
if __name__ == '__main__':
	import unittest
	unittest.main()
	