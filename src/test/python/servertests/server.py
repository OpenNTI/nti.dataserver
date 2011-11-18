import os
import sys
import time
import socket
import anyjson
import urllib2
import subprocess
import collections

from servertests.contenttypes import Note
from servertests.contenttypes import Canvas
from servertests.contenttypes import Sharable
from servertests.contenttypes import Highlight
from servertests.contenttypes import adaptDSObject
from servertests.contenttypes import CanvasPolygonShape

#########################

__all__ = ['DataserverProcess', 'DataserverClient' ]

#########################

_COVERAGE_CMD = '/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin/coverage'
_APP_PATH = os.path.dirname( __file__ ) + '/../../../main/python/app.py'
_APP_PATH_COV = os.path.dirname( __file__ ) + '/../../../main/python/app_coverage.py'
_COVERAGE_CONF =  os.path.dirname( __file__ ) + '/../../../main/python/_coverage_run.cfg'

def objectPath(obj):
	oid = obj
	if hasattr(obj, 'id'):
		oid = obj.id
	if 'OID' in oid:
		oid = oid['OID']
	return 'Objects/%s' % oid

class DataserverProcess(object):

	SERVER			= None
	PARENT_DIR		= "~/tmp"
	DATA_FILE_NAME	= "test.fs"
	VOID			= None
	ZEOSOCKET		= "/zeosocket"
	DEVNULL			= "/dev/null"
	KEY_TEST_WAIT	= 'TEST_WAIT'
	WRITE_ARG		= 'w'
	PORT			= 8080
	PORT_COV		= 6060
	LOCALHOST		= 'localhost'
	ENDPOINT		= 'http://%s:%s/dataserver' % (LOCALHOST, PORT)
	SERVER_DELAY	= 3

	def __init__(self):
		self.process = None

	def isRunning(self):
		return self._send_message(self.LOCALHOST, self.PORT)

	is_running = isRunning

	def _send_message(self, ip, port, message=None, do_shutdown=True):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			sock.connect((ip, int(port)))
			if message:
				sock.send(message)

			if do_shutdown:
				sock.shutdown(2)

			return True
		except:
			return False
		finally:
			sock.close()

	# -----------------------------------

	def startServer(self, path=_APP_PATH, blockIntervalSeconds=1, maxWaitSeconds=30):
		self._start_process([sys.executable, path], blockIntervalSeconds, maxWaitSeconds)

	start_server = startServer

	def startServerWithCoverage(self, path=_APP_PATH_COV, blockIntervalSeconds=1, maxWaitSeconds=30):
		self._start_process([sys.executable, path], blockIntervalSeconds, maxWaitSeconds)

	start_server_with_coverage  = startServerWithCoverage

	def _start_process(self, args, block_interval_seconds=1, max_wait_secs=30):

		if self.process or self.isRunning():
			print 'Dataserver already running.  Won\'t start a new one'
			return

		print 'Starting dataserver'

		if 'DATASERVER_DIR' not in os.environ:
			os.environ['DATASERVER_DIR'] = os.path.expanduser(self.PARENT_DIR)

		devnull = open(self.DEVNULL, self.WRITE_ARG) if 'DATASERVER_NO_REDIRECT' not in os.environ else None

		self.process = subprocess.Popen(args, stdin=devnull, stdout=devnull, stderr=devnull)
		if devnull is not None:
			devnull.close()

		elapsed = 0
		while elapsed <= max_wait_secs and not self.isRunning():
			time.sleep(block_interval_seconds)
			elapsed = elapsed + block_interval_seconds

		if elapsed >= max_wait_secs:
			raise Exception("Could not start data server")

		if self.KEY_TEST_WAIT in os.environ:
			time.sleep( int( os.environ[self.KEY_TEST_WAIT] ) )

	# -----------------------------------

	def terminateServer(self, blockIntervalSeconds=1, maxWaitSeconds=30):
		if self.process:
			self.process.terminate()
			return self._wait_for_termination(blockIntervalSeconds, maxWaitSeconds)
		else:
			return False

	terminate_server = terminateServer

	def terminateServerWithCoverage(self, report=True, block_interval_seconds=1, max_wait_secs=30):
		command  = 'terminate-and-report' if report else 'terminate'
		if self.process and self._send_message(self.LOCALHOST, self.PORT_COV, command, False):
			return self._wait_for_termination(block_interval_seconds, max_wait_secs)
		else:
			return False

	terminate_server_with_coverage = terminateServerWithCoverage

	def _wait_for_termination(self, block_interval_seconds=1, max_wait_secs=30):

		print 'Terminating dataserver'

		elapsed = 0
		while  elapsed <= max_wait_secs and self.isRunning():
			time.sleep(block_interval_seconds)
			elapsed = elapsed + block_interval_seconds

		if elapsed >= max_wait_secs:
			print "Could not stop data server"
			return False

		return True

	# -----------------------------------

	def _execute_call(self, command ):
		if not subprocess.call(command):
			print "Could not execute '%s' correctly " % ' '.join(command)
			return False
		return True

# -----------------------------------

DEFAULT_IS_ADAPT = True

def _http_ise_error_logging(f):
	def to_call( *args, **kwargs ):
		try:
			return f( *args, **kwargs )
		except urllib2.HTTPError as http:
			# If the server sent us anything,
			# try to use it
			_, _, tb = sys.exc_info()
			try:
				http.msg += ' URL: ' + http.geturl()
				body = http.read()
				# The last 20 or so lines
				http.msg += ' Body: ' + str( body )[-1600:]
			except (AttributeError, IOError): pass
			http.msg += '\n Args: ' + str(args)
			http.msg += '\n KWArgs: ' + str(kwargs)
			# re-raise the original exception object
			# with the original traceback
			raise http, None, tb
	return to_call

class DataserverClient(object):

	endpoint = None
	credentials = (None, None) #Tuple of username, password

	def __init__(self, endpoint):
		self.endpoint = endpoint
		if self.endpoint[-1] != '/':
			self.endpoint += '/'

	def setCredentials(self, credentials=None, user=None, passwd=None):
		self.credentials = credentials if credentials else (user, passwd)

	def clearCredentials(self):
		self.credentials = (None, None)

	@_http_ise_error_logging
	def getPath(self, path, credentials=None, adapt=DEFAULT_IS_ADAPT):
		request = self.buildRequest(path, credentials)
		response = urllib2.urlopen(request)
		return self.processResponse(response, adapt)

	@_http_ise_error_logging
	def createObjectAtPath(self, path, obj, credentials=None, adapt=DEFAULT_IS_ADAPT):
		obj = self.objectToPersist(obj)
		request = self.buildRequest(path, credentials, method='POST', data=anyjson.serialize(obj))
		response = urllib2.urlopen(request)
		return self.processResponse(response, adapt)

	@_http_ise_error_logging
	def updateObjectAtPath(self, path, obj, credentials=None, adapt=DEFAULT_IS_ADAPT):
		obj = self.objectToPersist(obj)
		request = self.buildRequest(path, credentials, method='PUT', data=anyjson.serialize(obj))
		response = urllib2.urlopen(request)
		return self.processResponse(response, adapt)

	@_http_ise_error_logging
	def deleteObjectAtPath(self, path, credentials=None, adapt=DEFAULT_IS_ADAPT):
		request = self.buildRequest(path, credentials, method='DELETE')
		response = urllib2.urlopen(request)
		return self.processResponse(response, adapt, expectingResult=False)

	def objectToPersist(self, obj):
		if hasattr(obj, 'toDataServerObject'):
			obj = obj.toDataServerObject()
		return obj

	def processResponse(self, response, adapt, expectingResult=True):
		result = None

		if expectingResult:
			result = anyjson.deserialize(response.read())
			if adapt:
				result = adaptDSObject(result)

		response.close()

		return result



	def updateObject(self, obj, oid=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		if not oid:
			oid = obj.id if hasattr(obj, 'id') else obj['OID']
		return self.updateObjectAtPath(objectPath(oid), obj, credentials=credentials, adapt=adapt)

	def deleteObject(self, obj, credentials=None, adapt=DEFAULT_IS_ADAPT):
		self.deleteObjectAtPath(objectPath(obj), credentials=credentials, adapt=adapt)

	def getObject(self, theId, credentials=None, adapt=DEFAULT_IS_ADAPT):
		return self.getPath(objectPath(theId), credentials=credentials, adapt=adapt)

	def sharedObjWithID(self, theID, target_s, credentials=None, adapt=DEFAULT_IS_ADAPT):
		return self.updateObjectAtPath(objectPath(theID), {'sharedWith' : target_s})

	def createNote(self, noteInfo, container, inReplyTo=None, sharedWith=None, adapt=DEFAULT_IS_ADAPT, **kwargs):
		body = self.createTextAndBody(noteInfo)
		note = Note(body=body, container=container, inReplyTo=inReplyTo, sharedWith=sharedWith, **kwargs)
		return self.createObject(note, adapt=adapt, **kwargs)

	def createTextAndBody(self, noteInfo):
		if isinstance(noteInfo, basestring):
			body = [noteInfo]
		elif isinstance(noteInfo, list):
			body = noteInfo
		elif isinstance(noteInfo, collections.Iterable):
			body = list(noteInfo)
		else:
			body = [noteInfo]
		return body

	def createHighlight(self, startHighlightedText, container, adapt=DEFAULT_IS_ADAPT, **kwargs):
		highlight = Highlight(startHighlightedText=startHighlightedText, container=container, **kwargs)
		return self.createObject(highlight, adapt=adapt, **kwargs)

	def createCanvas(self, sides, tx, ty, container, adapt=DEFAULT_IS_ADAPT, **kwargs):
		polygonShape = CanvasPolygonShape(sides=sides, container=container, **kwargs)
		canvas = Canvas(shapeList=[polygonShape], container=container, **kwargs)
		return canvas

	def createFriendsListWithNameAndFriends(self, name, friends, user=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		return self.createFriendsList({'Username': name, 'friends': friends}, credentials=credentials, adapt=adapt)

	def createFriendsList(self, obj, user=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		#FIXME: some copy/paste happening here and in next few methods
		creds = self._credentialsToUse(credentials)
		user = user or creds[0]
		path = '/users/%s/FriendsLists/' % user
		return self.createObjectAtPath(path, obj, credentials=creds, adapt=adapt)

	# -----------------------------------

	def shareObject(self, obj, targetOrTargets, credentials=None, adapt=DEFAULT_IS_ADAPT):
		if isinstance(obj, Sharable):
			obj.shareWith(targetOrTargets)
		else:
			targets = targetOrTargets
			if not isinstance(targets, list):
				targets = [targets]

			obj['sharedWith'].extend(targets)

		return self.updateObject(obj, credentials=credentials, adapt=adapt)

	def unshareObject(self, obj, targetOrTargets, credentials=None, adapt=DEFAULT_IS_ADAPT):
		if isinstance(obj, Sharable):
			obj.revokeSharing(targetOrTargets)
		else:
			targets = targetOrTargets
			if not isinstance(targets, list):
				targets = [targets]

			for target in targets:
				obj['sharedWith'].remove(target)

		return self.updateObject(obj, credentials=credentials, adapt=adapt)

	def createObject(self, obj, credentials=None, objType=None, container=None, adapt=DEFAULT_IS_ADAPT, **kwargs):
		if not objType:
			objType = obj.get('Class', None) or getattr(obj, 'DATASERVER_CLASS', None)

		if not objType:
			raise AttributeError('Must provide the type (Class) of the object')

		if not container:
			container = obj.get('ContainerId', None) or obj.get('container', None)

		if not container:
			raise AttributeError('Must provide the containerId of the object')

		# we special case notes and highlights so they are created in the same manor as the application
		if objType == 'Note' or objType == 'Highlight' or objType == 'Canvas':
			return self._createObjectViaTypeContainerEndpoint(obj, objType+'s', container, credentials, adapt=adapt)
		else:
			raise AttributeError('Unknown type %s', objType)

	def getUserObject(self, user=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		creds = self._credentialsToUse(credentials)
		user = user or creds[0]
		pathToGet = '/users/%s' % user
		return self.getPath(pathToGet, credentials=creds, adapt=adapt)

	def getFriendsLists(self, user=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		creds = self._credentialsToUse(credentials)
		user = user or creds[0]
		pathToGet = '/users/%s/FriendsLists' % user
		return self.getPath(pathToGet, credentials=creds, adapt=adapt)

	def getUserGeneratedData(self, container, user=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		creds = self._credentialsToUse(credentials)
		user = user or creds[0]
		pathToGet = '/users/%s/Pages/%s/UserGeneratedData' % (user, container)
		return self.getPath(pathToGet, credentials=creds, adapt=adapt)

	def getRecursiveStreamData(self, container, user=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		creds = self._credentialsToUse(credentials)
		user = user or creds[0]
		pathToGet = '/users/%s/Pages/%s/RecursiveStream' % (user, container)
		return self.getPath(pathToGet, credentials=creds, adapt=adapt)

	def getTranscripts(self,container, user=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		creds = self._credentialsToUse(credentials)
		user = user or creds[0]
		pathToGet = '/users/%s/Transcripts/%s' % (user, container)
		return self.getPath(pathToGet, credentials=creds, adapt=adapt)

	def executeUserSearch(self, search, credentials=None, adapt=DEFAULT_IS_ADAPT):
		creds = self._credentialsToUse(credentials)
		pathToGet = '/UserSearch/%s' % (search)
		return self.getPath(pathToGet, credentials=creds, adapt=adapt)

	# -----------------------------------

	def searchUserContent(self, query, user=None, credentials=None, adapt=DEFAULT_IS_ADAPT):
		creds = self._credentialsToUse(credentials)
		user = user or creds[0]
		pathToGet = '/users/%s/Search/RecursiveUserGeneratedData/%s' % (user, query)
		return self.getPath(pathToGet, credentials=creds, adapt=adapt)

	# -----------------------------------

	def _createObjectViaTypeContainerEndpoint(self, obj, otype, container, credentials,  adapt):
		credentials = self._credentialsToUse(credentials)
		user, _ = credentials
		pathToCreate = '/users/%s/%s/%s' % (user, otype, container)
		return self.createObjectAtPath(pathToCreate, obj, credentials=credentials, adapt=adapt)

	def buildRequest(self, path, passedCreds, method=None, data=None, headers=None):

		url = self.makeUrl(path)

		creds = self._credentialsToUse(passedCreds)
		user, passwd = creds

		if user and passwd:
			auth = urllib2.HTTPPasswordMgrWithDefaultRealm()
			auth.add_password(None, url, user, passwd)
			authendicated = urllib2.HTTPBasicAuthHandler(auth)
			opener = urllib2.build_opener(authendicated)
			urllib2.install_opener(opener)

		request = urllib2.Request(url, data=data)
		if headers:
			request.headers = headers
		if method:
			request.get_method = lambda: method

		return request

	# abstract away waiting.  Right now we just wait the max
	# time but it will most certainly change.
	# Some things still take longer than we were waiting
	def waitForEvent(self, event=None, maxWaitSeconds=3):
		if maxWaitSeconds and maxWaitSeconds > 0:
			time.sleep(maxWaitSeconds)
		return

	def makeUrl(self, path):
		return self.endpoint + (lambda x: x[1:] if x[0] == '/' else x)(path)

	def _credentialsToUse(self, passedCredentials):
		return passedCredentials or self.credentials


