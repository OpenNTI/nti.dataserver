import json
import plistlib
import threading
import collections

from collections import OrderedDict
from servertests.wsclient import WebSocketException
from servertests.wsclient import create_ds_connection

# -----------------------------

WS_ACK			= "6::"
WS_CONNECT		= "1::"
WS_DISCONNECT	= "0::"
WS_HEART_BEAT	= "2::"
WS_MESSAGE		= "3::"
WS_BROADCAST	= "5:::"

SERVER_KILL		= 'serverkill'

EVT_MESSAGE			= 'message'
EVT_ENTER_ROOM		= 'chat_enterRoom'
EVT_ENTERED_ROOM	= 'chat_enteredRoom'
EVT_EXITED_ROOM		= 'chat_exitedRoom'
EVT_POST_MESSOGE	= 'chat_postMessage'
EVT_RECV_MESSAGE	= 'chat_recvMessage'
EVT_MAKE_MODERATED	= 'chat_makeModerated'
EVT_RECV_MSG_MOD	= 'chat_recvMessageForModeration'
EVT_APPROVE_MSGS	= 'chat_approveMessages'
EVT_SHADOW_USERS	= 'chat_shadowUsers'
EVT_PRESENCE_OF_USER_CHANGE_TO = 'chat_presenceOfUserChangedTo'

DEFAULT_CHANNEL = "DEFAULT"
WHISPER_CHANNEL	= "WHISPER"

# -----------------------------

class _Room():
	def __init__(self, ID, occupants, moderated=False, active=True):
		self.ID = ID
		self.active = active
		self.occupants = occupants
		self.moderated = moderated
	
	def __str__(self):
		return self.ID
	
	def __eq__( self, other ):
		if isinstance(other, basestring):
			return self.ID == other
		elif isinstance(other, _Room):
			return self.ID == other.ID
		else:
			return False
		
class _Message(object):
	def __init__(self, text, containerId, channel=DEFAULT_CHANNEL):
		self.text = text
		self.channel = channel
		self.containerId = containerId

	def __str__(self):
		return self.text

	def __repr__(self):
		return "<%s,%s>" % (self.__class__.__name__,self.text)
	
class _RecvMessage(_Message):
	def __init__(self, text,  ID, containerId, creator, channel=DEFAULT_CHANNEL,\
				 lastModified=None, inReplyTo=None, recipients=None):
		
		super(_RecvMessage, self).__init__(text, containerId, channel)
		self.ID = ID
		self.creator = creator
		self.inReplyTo = inReplyTo
		self.recipients = recipients
		self.lastModified = lastModified
	
	def __eq__( self, other ):
		if isinstance(other, basestring):
			return self.ID == other
		elif isinstance(other, _RecvMessage):
			return self.ID == other.ID
		else:
			return False
		
	def __repr__(self):
		return "<%s,%s,%s>" % (self.__class__.__name__,self.ID,self.text)
		
class _PostMessage(_Message):
	def __init__(self, text, containerId, channel=DEFAULT_CHANNEL, recipients=None, inReplyTo=None):
		super(_PostMessage, self).__init__(text, containerId, channel)
		self.inReplyTo = inReplyTo
		self.recipients = recipients
	
	def __eq__( self, other ):
		if isinstance(other, basestring):
			return self.text == other
		elif isinstance(other, _PostMessage):
			return self.text == other.text
		else:
			return False
		
class Graph(object):
	def __init__(self, *args, **kwargs):
		
		self.rooms = {}
		self.sent_messages = []
		self.recv_messages = OrderedDict()
		self.moderated_messages = OrderedDict()
		
		self.ws_sent = None
		self.ws_recv = None
		self.killed = False
		self.heart_beats = 0
		
		self.ws = kwargs.get('ws', None)
		self.host = kwargs.get('host', None)
		self.port = kwargs.get('port', 8080)
		self.timeout = kwargs.get('timeout', 15)
		self.username = kwargs.get('username', None)
		self.password = kwargs.get('password', 'temp001')
		self.data_format = kwargs.get('data_format', 'json')
		self.connected = getattr(self.ws, "connected", False) if self.ws else False

		self.timeout = self.timeout or 15
		self.data_format = self.data_format or 'json'
		
	# ---- --------- ----
	
	@property
	def received(self):
		for m in self.recv_messages.itervalues():
			yield m.text
		
	@property	
	def sent(self):
		for m in self.sent_messages:
			yield m.text
			
	@property	
	def moderated(self):
		for m in self.moderated_messages:
			yield m.text
			
	# ---- Callbacks ----
	
	def serverKill(self, args=None):
		self.killed = True
		self.connected = False
		
	def connect(self):
		self.connected = True
	
	def disconnect(self):
		self.connected = False
	
	def heartBeat(self):
		self.connected = True
		self.heart_beats += 1
	
	def enterRoom(self, occupants):
		return _enterRoom(self.ws, occupants, self.data_format)
	
	def makeModerated(self, containerId, flag=True):
		_makeModerated(self.ws, containerId, flag, self.data_format)
				
	def approveMessages(self, mids):
		_approveMessages(self.ws, mids, self.data_format)
		
	def shadowUsers(self, containerId, users):
		_shadowUsers(self.ws, containerId, users, self.data_format)
		
	chat_enterRoom = enterRoom 
	chat_shadowUsers = shadowUsers
	chat_makeModerated = makeModerated
	chat_approveMessage = approveMessages
	
	# ---- ----- ----
	
	def chat_presenceOfUserChangedTo(self, username, status):
		pass
	
	def chat_enteredRoom(self, ID, occupants, moderated=False, active=True):
		self.rooms[ID] = _Room(ID, occupants, moderated, active)
	
	def chat_recvMessage(self, text,  ID, containerId, creator, channel=DEFAULT_CHANNEL,\
						 lastModified=None, inReplyTo=None, recipients=None):
		
		d = dict(locals())
		d.pop('self', None)
		self.recv_messages[ID] = _RecvMessage(**d)
	
	def chat_postMessage(self, text, containerId, channel=DEFAULT_CHANNEL, recipients=None, inReplyTo=None):
		d = dict(locals())
		d.pop('self', None)
		_postMessage(ws=self.ws,data_format=self.data_format, **d)
		self.sent_messages.append(_PostMessage(**d))
	
	def chat_recvMessageForModeration(self, text,  ID, containerId, creator, channel=DEFAULT_CHANNEL,\
						 			  lastModified=None, inReplyTo=None, recipients=None):
		
		d = dict(locals())
		d.pop('self', None)
		self.moderated_messages[ID] = _RecvMessage(**d)
		
	postMessage = chat_postMessage
	recvMessage = chat_recvMessage
	recvMessageForModeration = chat_recvMessageForModeration
	
	# ---- ----- ----
	
	def runLoop(self):
		self.killed = False
		try:
			if not self.ws:
				self.ws_connect()
			else:
				self.connected = getattr(self.ws, "connected", False)
				
			while self.connected or not self.killed:
				_next_event(self.ws, self)
		finally:
			self.ws_capture()
	
	def nextEvent(self):
		return _next_event(self.ws, self)
	
	# ---- WebSocket ----
	
	def ws_connect(self):
		
		if self.ws_connected:
			self.ws.close()
			
		self.ws = _ws_connect(self.host, self.port, username=self.username,\
							  password=self.password, timeout=self.timeout)
				
		self.connected = getattr(self.ws, "connected", False)
		
	def ws_close(self):
		if self.ws_connected:
			try:
				_ws_disconnect(self.ws)
				self.ws.close()
			finally:
				self.ws = None
		self.connected = False
		
	def ws_capture(self, reset=True):
		self.ws_sent = list(message_ctx.sent)
		self.ws_recv = list(message_ctx.received)
		if reset: message_ctx.reset()
		
	def ws_capture_and_close(self, reset=True):
		self.ws_capture(reset=reset)
		self.ws_close()
		
	@property
	def ws_connected(self):
		return getattr(self.ws, "connected", False) if self.ws else False
	
	@property
	def ws_last_recv(self):
		return message_ctx.last_recv
	
	@property
	def ws_last_sent(self):
		return message_ctx.last_sent
				
# -----------------------------

class MessageContext(threading.local):
	def __init__(self):
		self._sent=[]
		self._recv=[]
	
	def recv(self, ws):
		msg = ws.recv()
		self._recv.append(msg)
		return msg
	
	def send(self, ws, msg):
		ws.send(unicode(msg))
		self._sent.append(msg)
		return msg
	
	def reset(self):
		self._sent=[]
		self._recv=[]
		
	@property
	def sent(self):
		return self._sent
	
	@property
	def received(self):
		return self._recv
	
	@property
	def last_recv(self):
		return None if len(self._recv) == 0 else self._recv[-1]
	
	@property
	def last_sent(self):
		return None if len(self._sent) == 0 else self._sent[-1]
	
message_ctx = MessageContext()

# -----------------------------

class Serverkill(WebSocketException):
	def __init__(self, args=None):
		super(Serverkill, self).__init__(str(args) if args else '')
		
class InvalidAuthorization(WebSocketException):
	def __init__(self, username, password=''):
		super(InvalidAuthorization, self).__init__('Invalid credentials for %s' % username)
		self.username = username
		self.password = password

class InvalidDataFormat(WebSocketException):
	def __init__(self, data_format=''):
		super(InvalidDataFormat, self).__init__('Invalid data format %s' % data_format)
		self.data_format = data_format
		
class CouldNotEnterRoom(WebSocketException):
	def __init__(self, room_id=''):
		super(CouldNotEnterRoom, self).__init__('Could not enter room %s' % room_id)
		
class NotEnoughOccupants(WebSocketException):
	def __init__(self, room_id=''):
		super(NotEnoughOccupants, self).__init__('room %s does not have enough occupants' % room_id)
	
class InActiveRoom(WebSocketException):
	def __init__(self, room_id=''):
		super(InActiveRoom, self).__init__('Room is inactive %s' % room_id)
		
# -----------------------------

def toList(data, unique=True):
	if data:
		if isinstance(data, basestring) or not isinstance(data, collections.Iterable):
			data = [data]
		elif not isinstance(data, list):
			data = list(set(data)) if unique else list(data)
	return data
		
# -----------------------------

def isConnect(msg):
	return str(msg).startswith(WS_CONNECT)

def isBroadCast(msg):
	return str(msg).startswith(WS_BROADCAST)

def isHeartBeat(msg):
	return str(msg).startswith(WS_HEART_BEAT)

def encode(data, data_format='json'):
	if data_format == 'json':
		return json.dumps(data)
	elif data_format == 'plist':
		return plistlib.writePlistToString(data)
	return None
		
def decode(msg, data_format='json'):
	if msg and msg.startswith(WS_BROADCAST):
		msg = msg[len(WS_BROADCAST):]
		if data_format == 'json':
			return json.loads(msg)
		elif data_format == 'plist':
			return plistlib.readPlistFromString(msg)
	return None

def isEvent(data, event, data_format='json'):	
	if isinstance(data, basestring):
		data = decode(data, data_format)
	if isinstance(data, dict):
		return data.get('name',None) == event
	return False

def isServerKill(data, data_format='json'):
	return isEvent(data, SERVER_KILL, data_format)
	
def isRecvMessage(data, data_format='json'):
	return isEvent(data, EVT_RECV_MESSAGE, data_format)
	
def isEnteredRoom(data, data_format='json'):
	return isEvent(data, EVT_ENTERED_ROOM, data_format)

def isPresenceOfUserChangedTo(data, data_format='json'):
	return isEvent(data, EVT_PRESENCE_OF_USER_CHANGE_TO, data_format)

def isRecv4Moderation(data, data_format='json'):
	return isEvent(data, EVT_RECV_MSG_MOD, data_format)

def isApproveMessages(data, data_format='json'):
	return isEvent(data, EVT_APPROVE_MSGS, data_format)

def _nonefy(s):
	return None if s and str(s) == 'null' else s

def _next_event(ws, graph=None):
	msg = message_ctx.recv(ws)
	if graph and isinstance(graph, Graph):
		if isConnect(msg):
			graph.connect()
		elif isHeartBeat(msg):
			graph.heartBeat()
		elif isBroadCast(msg):
			d = decode(msg)
			if isServerKill(d): 
				graph.serverKill(args=d.get('args', None))
			elif isEnteredRoom(d):
				d = d['args'][0]
				graph.chat_enteredRoom(	ID=d['ID'], occupants=d['Occupants'],\
										moderated= d['Moderated'], active=d['Active'])
			elif isRecvMessage(d) or isRecv4Moderation(d):
				moderated = isRecv4Moderation(d)
				d = d['args'][0]	
				d = { 'text':d['Body'], 'ID':d['ID'], 'containerId':d['ContainerId'], \
					  'creator': d['Creator'], 'channel':d.get('channel', DEFAULT_CHANNEL),\
					  'lastModified': d.get('Last Modified', 0),
					  'inReplyTo': _nonefy(d.get('inReplyTo', None)),
					  'recipients': _nonefy(d.get('recipients', None)) }
					
				if not moderated:
					graph.chat_recvMessage(	**d)
				else:
					graph.chat_recvMessageForModeration(**d)
									
			elif isPresenceOfUserChangedTo(d):
				d = d['args']
				graph.chat_presenceOfUserChangedTo(username=d[0], status=d[1])
				
	return msg
			
def _enterRoom(ws, occupants, data_format='json'):
	occupants = toList(occupants)
	args = {"Occupants": occupants}
	d = {"name":EVT_ENTER_ROOM, "args":[args]}
	msg = encode(d, data_format)
	if msg:
		msg = WS_BROADCAST + msg
		message_ctx.send(ws, msg)
	else:
		raise InvalidDataFormat(data_format)
			
	return (None, None)

def _postMessage(ws, containerId, text, channel=DEFAULT_CHANNEL, recipients=None, inReplyTo=None ,data_format='json'):
	
	args = {"ContainerId": containerId, "Body": unicode(text), "Class":"MessageInfo"}
	if channel and channel != DEFAULT_CHANNEL:
		args['channel'] = channel
	
	if recipients:
		args['recipients'] = recipients
		
	if inReplyTo:
		args['inReplyTo'] = inReplyTo
		
	d = {"name":EVT_POST_MESSOGE, "args":[args]}
	msg = encode(d, data_format)	
	if msg:
		msg = WS_BROADCAST + msg
		message_ctx.send(ws, msg)
	else:
		raise InvalidDataFormat(data_format)
		
def _makeModerated(ws, containerId, flag=True, data_format='json'):
	
	d = {"name":EVT_MAKE_MODERATED, "args":[containerId, flag]}
	msg = encode(d, data_format)	
	if msg:
		msg = WS_BROADCAST + msg
		message_ctx.send(ws, msg)
	else:
		raise InvalidDataFormat(data_format)
	
def _approveMessages(ws, mids, data_format='json'):
	mids = toList(mids)
	d = {"name":EVT_APPROVE_MSGS, "args":[mids]}
	msg = encode(d, data_format)
	if msg:
		msg = WS_BROADCAST + msg
		message_ctx.send(ws, msg)
	else:
		raise InvalidDataFormat(data_format)
	
def _shadowUsers(ws, containerId, users, data_format='json'):
	users = toList(users)
	d = {"name":EVT_SHADOW_USERS, "args":[containerId, users]}
	msg = encode(d, data_format)
	if msg:
		msg = WS_BROADCAST + msg
		message_ctx.send(ws, msg)
	else:
		raise InvalidDataFormat(data_format)

# -----------------------------

def _ws_disconnect(ws, data_format='json'):
	d = {"name":WS_DISCONNECT, "args":[]}
	msg = encode(d, data_format)	
	message_ctx.send(ws, msg)
	
def _ws_connect(host, port, username, password='temp001', timeout=15):

	# create the connectiona and do a handshake. 
	ws = create_ds_connection(host, port, timeout=timeout)
	
	# send connection string
	d = {"args":[username, password]}
	msg = '%s%s' % (WS_BROADCAST, encode(d,'json'))
	message_ctx.send(ws, msg)
	
	return ws
