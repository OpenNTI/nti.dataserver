import time
import random
import threading

from user_chat_objects import OneRoomUser
from user_chat_objects import BasicChatTest

class TestShadowedChat(BasicChatTest):
	
	def setUp(self):
		super(TestShadowedChat, self).setUp()	
		self.users = self.user_names[:3]
	
	def _launch(self, threads, user, args):
		t=threading.Thread(target=user, kwargs=args)
		threads[user] = t 
		t.start()
		return t
		
	def test_chat(self):
		connect_event = threading.Event()
		
		occupants = self.users[1:]
		ghost = Ghost(username=self.users[0], occupants=occupants)
		chatters = [User(username=u) for u in occupants]
	
		threads = {}
		args={'connect_event':connect_event, 'users_to_shadow':self.users[1]}
		self._launch(threads, ghost, args)
		
		# wait till ghost connects
		time.sleep(1.0)
		
		# start chatters
		entries = random.randint(10, 20)
		print "entries", entries
		
		for user in chatters:
			args={'entries':entries, 'connect_event':connect_event}
			self._launch(threads, user, args)
			
		for t in threads.itervalues():
			t.join()
			
		# ------ do checks ------
		
		for u in threads.iterkeys():
			self.assert_(u.exception == None, "User %s exception %s" % (u.username, u.exception))
		
		shadowed_user = chatters[0]
		ghost_msgs = ghost.recv_messages
		shadowed_msgs = shadowed_user.recv_messages
	
		self.assertEqual(2*len(shadowed_msgs), len(ghost_msgs), \
						"Ghost %s did not get all messages from shadowed %s" % (ghost, shadowed_user))
		
		for k, _ in shadowed_msgs.items():
			self.assert_(ghost_msgs.has_key(k), "Ghost %s did not get message with id %s" % (ghost, k))

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
			
class Ghost(User):
		
	def __init__(self, username, occupants):
		super(Ghost, self).__init__(username=username)
		self.occupants = occupants
		self.online = set()
	
	def chat_presenceOfUserChangedTo(self, username, status):
		if status == 'Online' and username in self.occupants:
			self.online.add(username)
			print 'entered', username
			self.heart_beats = 0
		
	def __call__(self, connect_event, users_to_shadow):
		t = time.time()
		try:
			self.ws_connect()
			
			# wait users are connected
			
			self.heart_beats = 0
			while self.heart_beats < 5 and len(self.online) < len(self.occupants):
				self.nextEvent()				
				
			self.enterRoom(self.occupants)
			self.wait_4_room()	
			self.shadowUsers(self.room, users_to_shadow)		
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
	