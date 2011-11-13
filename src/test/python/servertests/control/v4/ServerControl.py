import os
import json
import urllib2
import plistlib
import cStringIO

from time import mktime
from wsgiref import handlers
from datetime import datetime
from servertests.control import v4

##########################

_APP_PATH = os.path.dirname( __file__ ) + '/../../main/python/app.py'
VOID_VALUE = 'has not been set'

class DefaultValues(object):

	def __init__(self):
		self.path                 = _APP_PATH
		self.username             = 'ltesti'
		self.otherUser            = 'sjohnson'
		self.password             = 'temp001'
		self.incorrectpassword    = 'incorrect'
		self.message              = None
		self.void                 = None
		self.TinyNumber           = 0
		self.LonelyNumber         = 1
		self.TheNumberTwo         = 2
		self.TheNumberThree       = 3
		self.OK                   = 200
		self.SuccessfulAdd        = 201
		self.SuccessfulDelete     = 204
		self.NotModifiedSince     = 304
		self.Unauthorized         = 401
		self.Forbidden            = 403
		self.NotFound             = 404
		self.NotAllowed           = 405
		self.WrongType            = 500

#------------------------

class DeleteFunctionality(object):

	def successfulOpen(self):
		DeleteFunctionality.ServerController = ServerController()

	def failureToOpen404(self):
		pass

	def failureToOpenOther(self):
		pass

class FormatFunctionality(object):

	def urlFormat(self, URL, fmt):
		return URL + '?format=' + fmt

	def read(self): pass

	def write(self): pass

class NoFormat(FormatFunctionality):

	def formatURL(self, URL):
		return URL

	def write(self, data):
		return json.dumps(data)

	def read(self, request):
		return json.loads(request.read())

class JsonFormat(NoFormat):

	def formatURL(self, URL):
		return self.urlFormat(URL, 'json')

class PlistFormat(FormatFunctionality):

	def formatURL(self, URL):
		return self.urlFormat(URL, 'plist')

	def write(self, data):
		output = cStringIO.StringIO()
		plistlib.writePlist(data, output)
		data = output.getvalue()
		output.close()
		return data

	def read(self, request):
		return plistlib.readPlistFromString(request.read())

#------------------------

class UserObject(object):
	def __init__(self): pass
		
	def setUserID(self, ID):
		UserObject.IDUser = ID
		
	def getUserID(self):
		return UserObject.IDUser
	
	def setOtherUserID(self, ID):
		UserObject.IDOther = ID
		
	def getOtherUserID(self):
		return UserObject.IDOther
	
class OID_Remover(object):

	def removeOID(self, body):
		keys = body.keys()
		for key in keys:
			if isinstance(body[key], dict or list):
				self.removeOID(body[key])
		try:		
			del body['OID']
		except KeyError:
			pass
		try:
			del body["Creator"]
		except KeyError:
			pass
		
class URLFunctionality(object):

	def reset(self):
		self.responseCode			 = None
		self.body					 = None
		self.lastModified			 = None
		self.id						 = None
		self.ifModifiedSinceError	 = None
		self.ifModifiedSinceSuccess	 = None

	def setValues(	self, code=None, body=None, lastModified=None, aid=None,\
					ifModifiedSinceError=None, ifModifiedSinceSuccess=None):
		self.responseCode			 = code
		self.body					 = body
		self.lastModified			 = lastModified
		self.id						 = aid
		self.ifModifiedSinceError	 = ifModifiedSinceError
		self.ifModifiedSinceSuccess	 = ifModifiedSinceSuccess
		
#------------------------

class ServerController(object):
	
	ID_KEY					= 'ID'
	NOT_FOUND				= -1
	TIME_TO_REMOVE			= 100
	RESP_NOT_FOUND			= 404
	IF_LAST_MODIFIED_HEADER	= 'If-Modified-Since'
	LAST_MODIFIED_KEY		= 'Last Modified'
	FIND_FORMAT				= '?format='
	
	def __init__(self):
		self.requests	= ServerRequest()
		self.newID		= None

	def reset(self, username, password, info, userObject):
		self.info = info
		self.username = username
		self.password = password
		self.userObject = userObject

	create = reset
	
	def addID(self, URL, ID=None):
		if ID is None:
			return URL
		else:
			return URL + '/' + ID

	def postTest(self, URL, data=VOID_VALUE, username=VOID_VALUE,\
				password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=NoFormat(),\
				userObject=VOID_VALUE):
		
		if username == VOID_VALUE:
			username = self.username
		if password == VOID_VALUE:
			password = self.password
		if data == VOID_VALUE:
			data = self.info
		if userObject == VOID_VALUE:
			userObject = self.userObject
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		data = fmt.write(data)
		call = self.requests.post(formattedURL, username, password, data)
		try:
			request = urllib2.urlopen(call)
			parsedBody = fmt.read(request)
			bodyDataExtracter.setResponseCode(request.code)
			bodyDataExtracter.setParsedBody(parsedBody)
			request.close()
			self.newID = parsedBody['ID']
		except urllib2.HTTPError, error:
			bodyDataExtracter.setResponseCode(error.code)
			request = self.getBody(formattedURL, self.username, self.password, fmt)
			bodyDataExtracter.setParsedBody(request, userObject)

	def putTest(self, URL, data=VOID_VALUE, username=VOID_VALUE,\
				password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=NoFormat()):
		if username == VOID_VALUE:
			username = self.username
		if password == VOID_VALUE:
			password = self.password
		if data == VOID_VALUE:
			data = self.info
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		data = fmt.write(data)
		call = self.requests.put(formattedURL, data, username, password)
		try:
			request = urllib2.urlopen(call)
			parsedBody = fmt.read(request)
			bodyDataExtracter.setResponseCode(request.code)
			bodyDataExtracter.setParsedBody(parsedBody)
			request.close()
		except urllib2.HTTPError, error:
			bodyDataExtracter.setResponseCode(error.code)
			request = self.getBody(formattedURL, self.username, self.password, fmt)
			bodyDataExtracter.setParsedBody(request)

	def deleteTest(	self, URL, username=VOID_VALUE, password=VOID_VALUE,\
					bodyDataExtracter=VOID_VALUE, fmt=NoFormat()):
		
		if username == VOID_VALUE:
			username = self.username
		if password == VOID_VALUE:
			password = self.password
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		call = self.requests.delete(formattedURL, username, password)
		try:
			request = urllib2.urlopen(call)
			notFound = self.getBody(URL, username, password, fmt)
			bodyDataExtracter.setResponseCode(request.code)
			bodyDataExtracter.setParsedBody(notFound)
			request.close()
		except urllib2.HTTPError, error:
			bodyDataExtracter.setResponseCode(error.code)
			request = self.getBody(formattedURL, self.username, self.password, fmt)
			bodyDataExtracter.setParsedBody(request)

	def getIfLastModifiedNo(self, request, response):
		request.add_header(self.IF_LAST_MODIFIED_HEADER, response.headers.get(self.LAST_MODIFIED_KEY))
		try:
			result = urllib2.urlopen(request)
			result.close()
			return result.code
		except urllib2.HTTPError, error:
			return error.code

	def getIfLastModifiedYes(self, URL, username=VOID_VALUE, password=VOID_VALUE):
		request = self.requests.get(URL, username, password)
		now = datetime.now()
		stamp = mktime(now.timetuple())
		stamp -= self.TIME_TO_REMOVE
		GMTTime = handlers.format_date_time(stamp)
		request.headers[self.IF_LAST_MODIFIED_HEADER] = GMTTime
		try:
			result = urllib2.urlopen(request)
			result.close()
			return result.code
		except urllib2.HTTPError, error:
			return error.code

	def getLastModified(self, URL, ID=VOID_VALUE, fmt=NoFormat()):
		username = self.username
		password = self.password
		
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			URL = fmt.formatURL(URL)
		
		if ID != VOID_VALUE:
			URL = URL + '/' + ID
		call = self.requests.get(URL, username, password)
		try:
			request = urllib2.urlopen(call)
			parsedBody = fmt.read(request)
			timeModified = parsedBody[self.LAST_MODIFIED_KEY]
			request.close()
			return timeModified
		except urllib2.HTTPError, request:
			return request.code

	def getBody(self, URL, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		if username == VOID_VALUE:
			username = self.username
		if password == VOID_VALUE:
			password = self.password
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		call = self.requests.get(formattedURL, username, password)
		try:
			request = urllib2.urlopen(call)
			parsedBody = fmt.read(request)
			request.close()
			return parsedBody
		except urllib2.HTTPError, request:
			return request.code

	def setUpPut(self, URL, data=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		
		if username == VOID_VALUE:
			username = self.username
		if password == VOID_VALUE:
			password = self.password
		if data == VOID_VALUE:
			data = self.info
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		data = fmt.write(data)
		call = self.requests.put(formattedURL, data, username, password)
		request = urllib2.urlopen(call)
		#body = fmt.read(request)
		request.close()

	def setUpPost(self, URL, data=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		
		if username == VOID_VALUE:
			username = self.username
		if password == VOID_VALUE:
			password = self.password
		if data == VOID_VALUE:
			data = self.info
			
		#if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
		#	formattedURL = fmt.formatURL(URL)
		#else:
		#	formattedURL = URL
			
		data = fmt.write(data)
		call = self.requests.post(URL, username, password, data)
		request = urllib2.urlopen(call)
		body = fmt.read(request)
		request.close()
		return body['ID']

	def tearDownDelete(	self, URL, username=VOID_VALUE,\
						password=VOID_VALUE, fmt=NoFormat()):
		
		if username == VOID_VALUE:
			username = self.username
		if password == VOID_VALUE:
			password = self.password
			
		if URL.find(self.FIND_FORMAT) is self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		call = self.requests.delete(formattedURL, username, password)
		try:
			urllib2.urlopen(call)
		except urllib2.HTTPError, error:
			if error.code == self.RESP_NOT_FOUND:
				pass
			else:
				urllib2.HTTPError

class GetTest(ServerController):
	
	def run(self, constants, URL, data, username, password, bodyDataExtracter, fmt=NoFormat()):
		
		if username == VOID_VALUE:
			username = constants.username
		if password == VOID_VALUE:
			password = constants.password
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		call = self.requests.get(formattedURL, username, password)
		try:
			response = urllib2.urlopen(call)
			parsedBody = fmt.read(response)
			bodyDataExtracter.setResponseCode(response.code)
			bodyDataExtracter.setParsedBody(parsedBody)
			bodyDataExtracter.setIfModifiedSinceError(self.getIfLastModifiedNo(call, response))
			bodyDataExtracter.setIfModifiedSinceSuccess(self.getIfLastModifiedYes(formattedURL, username, password))
			response.close()
		except urllib2.HTTPError, request:
			bodyDataExtracter.setResponseCode(request.code)
			request = self.getBody(formattedURL, self.username, self.password, fmt)
			bodyDataExtracter.setParsedBody(request)
			
class GetLastModified(ServerController):
	
	def run(self, URL, constants, ID=VOID_VALUE, fmt=NoFormat()):
		username = constants.username
		password = constants.password
		
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			URL = fmt.formatURL(URL)
		
		if ID != VOID_VALUE:
			URL = URL + '/' + ID
		call = self.requests.get(URL, username, password)
		try:
			request = urllib2.urlopen(call)
			parsedBody = fmt.read(request)
			timeModified = parsedBody[self.LAST_MODIFIED_KEY]
			request.close()
			return timeModified
		except urllib2.HTTPError, request:
			return request.code
			
class SetUpPut(ServerController):
			
	def setUpPut(self, URL, constants, data=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		
		if username == VOID_VALUE:
			username = constants.username
		if password == VOID_VALUE:
			password = constants.password
		if data == VOID_VALUE:
			data = constants.DEFAULT_INFO
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		data = fmt.write(data)
		call = self.requests.put(formattedURL, data, username, password)
		request = urllib2.urlopen(call)
		request.close()
		
class SetUpPost(ServerController):
	
	def setUpPost(self, URL, constants, data=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		
		if username == VOID_VALUE:
			username = constants.username
		if password == VOID_VALUE:
			password = constants.password
		if data == VOID_VALUE:
			data = constants.DEFAULT_INFO
			
		data = fmt.write(data)
		call = self.requests.post(URL, username, password, data)
		request = urllib2.urlopen(call)
		body = fmt.read(request)
		request.close()
		return body['ID']
		
class GetBody(ServerController):
		
	def getBody(self, URL, constants, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		if username == VOID_VALUE:
			username = constants.username
		if password == VOID_VALUE:
			password = constants.password
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		call = self.requests.get(formattedURL, username, password)
		try:
			request = urllib2.urlopen(call)
			parsedBody = fmt.read(request)
			request.close()
			return parsedBody
		except urllib2.HTTPError, request:
			return request.code


#------------------------

class ServerRequest(object):

	def get(self, URL, username, password):
		request = urllib2.Request(url=URL)
		auth = urllib2.HTTPPasswordMgrWithDefaultRealm()
		auth.add_password(None, URL, username, password)
		authendicated = urllib2.HTTPBasicAuthHandler(auth)
		opener = urllib2.build_opener(authendicated)
		urllib2.install_opener(opener)
		return request

	def delete(self, URL, username, password):
		request = urllib2.Request(URL)
		auth = urllib2.HTTPPasswordMgrWithDefaultRealm()
		auth.add_password(None, URL, username, password)
		authendicated = urllib2.HTTPBasicAuthHandler(auth)
		opener = urllib2.build_opener(authendicated)
		urllib2.install_opener(opener)
		request.get_method = lambda: 'DELETE'
		return request

	def put(self, URL, data, username, password):
		request = urllib2.Request(URL, data)
		auth = urllib2.HTTPPasswordMgrWithDefaultRealm()
		auth.add_password(None, URL, username, password)
		authendicated = urllib2.HTTPBasicAuthHandler(auth)
		opener = urllib2.build_opener(authendicated)
		urllib2.install_opener(opener)
		request.get_method = lambda: 'PUT'
		return request

	def post(self, URL, username, password, data):
		request = urllib2.Request(URL, data)
		auth = urllib2.HTTPPasswordMgrWithDefaultRealm()
		auth.add_password(None, URL, username, password)
		authendicated = urllib2.HTTPBasicAuthHandler(auth)
		opener = urllib2.build_opener(authendicated)
		urllib2.install_opener(opener)
		return request

class PostTest(object):

	def postException(self, body, ID):
		print body['Items'][ID]
