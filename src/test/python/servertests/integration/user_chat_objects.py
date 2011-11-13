import uuid
import random
import collections

from websocket_interface import Graph
from websocket_interface import Serverkill
from websocket_interface import InActiveRoom
from websocket_interface import CouldNotEnterRoom
from websocket_interface import NotEnoughOccupants

from servertests import DataServerTestCase
from servertests.server import DataserverProcess

SOCKET_IO_HOST	= DataserverProcess.LOCALHOST
SOCKET_IO_PORT	= DataserverProcess.PORT

phrases = (	"Yellow brown", "Blue red green render purple?",\
			"Alpha beta", "Gamma delta epsilon omega.",\
			"One two", "Three rendered four five.",\
			"Quick went", "Every red town.",\
			"Yellow uptown",  "Interest rendering outer photo!",\
			"Preserving extreme", "Chicken hacker")

class BasicChatTest(DataServerTestCase):
		
	user_names = []

	@classmethod
	def setUpClass(cls):
		DataServerTestCase.setUpClass()
		cls.create_users()

	@classmethod
	def create_users(cls, max_users=5):
		
		for x in range(1,max_users):
			name = 'test.user.%s@nextthought.com' % x
			cls.user_names.append(name)
			
		for u in cls.user_names:
			friends = list(cls.user_names)
			friends.remove(u)
			cls.register_friends(username=u, friends=friends)
		
	@classmethod
	def generate_user_name(self):
		return '%s@nextthought.com' % str(uuid.uuid4()).split('-')[0]
		
	@classmethod
	def register_friends(cls, username, friends, password='temp001'):
		
		if isinstance(friends, basestring) or not isinstance(friends, collections.Iterable):
			friends = [friends]
		elif not isinstance(friends, list):
			friends = list(set(friends))
		
		list_name = 'cfl-%s-%s' % (username, str(uuid.uuid4()).split('-')[0])
		
		ds = cls.new_client((username, password))
		ds.createFriendsListWithNameAndFriends(list_name, friends)
		
		return list_name
		
class BasicUser(Graph):
	def __init__(self, **kwargs):
		if not kwargs.has_key('host'):
			kwargs['host'] = SOCKET_IO_HOST
		
		if not kwargs.has_key('port'):
			kwargs['port'] = SOCKET_IO_PORT
			
		Graph.__init__(self, **kwargs)
		self.exception = None
					
	def __str__(self):
		return self.username if self.username else self.socketio_url
	
	def __repr__(self):
		return "<%s,%s>" % (self.__class__.__name__,self.__str__())
	
	def serverKill(self, args=None):
		super(BasicUser, self).serverKill(args)
		raise Serverkill(args)
		
	def __call__(self, *args, **kwargs):
		pass
	
	def wait_heart_beats(self, max_beats=3):
		self.heart_beats = 0
		while self.heart_beats < max_beats:
			self.nextEvent()
				
	def generate_message(self, aMin=1, aMax=4):
		return " ".join(random.sample(phrases, random.randint(aMin, aMax)))
	
	def post_random_messages(self, room_id, entries=None, a_min=3, a_max=10):
		entries = entries or random.randint(a_min, a_max)
		for _ in xrange(entries):
			content = self.generate_message()
			self.chat_postMessage(text=unicode(content), containerId=room_id)
			
	@property
	def first_room(self):
		return self.rooms.keys()[0] if len(self.rooms) > 0 else None

class OneRoomUser(BasicUser):
		
	def __init__(self, **kwargs):
		super(OneRoomUser, self).__init__(**kwargs)
		self._room = None
		
	def chat_enteredRoom(self, **kwargs):
		super(OneRoomUser, self).chat_enteredRoom(**kwargs)
		rid = self.room
		if not rid:
			if not kwargs['active']:
				raise InActiveRoom(rid)
			else:
				occupants = kwargs.get('occupants', [])
				if len(occupants) <= 1:
					raise NotEnoughOccupants(rid)
		
	def chat_recvMessage(self, **kwargs):
		super(OneRoomUser, self).chat_recvMessage(**kwargs)
		cid = kwargs['containerId'] 
		creator = kwargs['creator'] 
		if cid == self.room and creator != self.username:
			self.heart_beats = 0
		else:
			self.recv_messages.pop(kwargs['ID'] , None)
			
	def wait_4_room(self, max_beats=5):
		self.heart_beats = 0
		while self.heart_beats < max_beats and not self.room:
			self.nextEvent()
		
		if self.heart_beats >= max_beats and not self.room:
			raise CouldNotEnterRoom()
				
	@property
	def room(self):
		if not self._room and len(self.rooms) > 0:
			self._room = self.first_room
		return self._room
	