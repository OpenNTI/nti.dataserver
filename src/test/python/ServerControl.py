import urllib2
import os
import sys
import json
import plistlib
import cStringIO
from datetime import datetime
from wsgiref import handlers
from time import mktime

_APP_PATH = os.path.dirname( __file__ ) + '/../../main/python/app.py'

class DefaultValues(object):

	def __init__(self):
		self.path                 = _APP_PATH
		self.username             = 'ltesti@nextthought.com'
		self.otherUser            = 'sjohnson@nextthought.com'
		self.password             = 'temp001'
		self.incorrectpassword    = 'incorrect@foo.bar' # This is also used as a username.
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

class DeleteFunctionality(object):

	def successfulOpen(self):
		DeleteFunctionality.ServerController = ServerController()

	def failureToOpen404(self):
		pass

	def failureToOpenOther(self):
		pass

class FormatFunctionality(object):

	def urlFormat(self, URL, format):
		return URL + '?format=' + format

	def read(self): pass

	def write(self): pass

class NoFormat(FormatFunctionality):

	def formatURL(self, URL):
		return URL

	def write(self, data):
		return json.dumps(data)

	def read(self, request):
		return json.loads(request.read())

class JsonFormat(FormatFunctionality):

	def formatURL(self, URL):
		return self.urlFormat(URL, 'json')

	def write(self, data):
		return json.dumps(data)

	def read(self, request):
		return json.loads(request.read())

class PlistFormat(FormatFunctionality):

	def formatURL(self, URL):
		return self.urlFormat(URL, 'plist')

	def write(self, dict):
		output = cStringIO.StringIO()
		plistlib.writePlist(dict, output)
		data = output.getvalue()
		output.close()
		return data

	def read(self, request):
		return plistlib.readPlistFromString(request.read())

class URLFunctionality(object):

	def reset(self):
		self.responseCode            = None
		self.body                    = None
		self.lastModified            = None
		self.id                      = None
		self.ifModifiedSinceError    = None
		self.ifModifiedSinceSuccess  = None

	def setValues(	self, code=None, body=None, lastModified=None, aid=None,\
					ifModifiedSinceError=None, ifModifiedSinceSuccess=None):
		self.responseCode            = code
		self.body                    = body
		self.lastModified            = lastModified
		self.id                      = aid
		self.ifModifiedSinceError    = ifModifiedSinceError
		self.ifModifiedSinceSuccess  = ifModifiedSinceSuccess

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

class ServerController(object):

	def __init__(self):
		self.FIND_FORMAT                = '?format='
		self.IF_LAST_MODIFIED_HEADER    = 'If-Modified-Since'
		self.LAST_MODIFIED_KEY          = 'Last Modified'
		self.ID_KEY                     = 'ID'
		self.randomValue                = '0'
		self.NOT_FOUND                  = -1
		self.FIRST_INDEX                = 0
		self.SECOND_INDEX               = 1
		self.TIME_TO_REMOVE             = 100
		self.RESP_NOT_FOUND             = 404
		ServerController.requests	    = ServerRequest()
		ServerController.Formatless     = NoFormat()
		ServerController.setActuals     = URLFunctionality()
		ServerController.newID          = None

	def create(self, username, password, info, userObject):
		self.username = username
		self.password = password
		self.info = info
		self.userObject = userObject

	def addID(self, URL, ID):
		if ID is None:
			return URL
		else:
			return URL + '/' + ID

	def setID(self):
		ServerController.ID = self.randomValue

	def getID(self):
		return ServerController.ID

	@_http_ise_error_logging
	def getTest(self, URL, username='has not been set', password='has not been set',\
				bodyDataExtracter='has not been set', format=NoFormat()):

		if username == 'has not been set':
			username = self.username
		if password == 'has not been set':
			password = self.password
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = format.formatURL(URL)
		else:
			formattedURL = URL
		call = ServerController.requests.get(formattedURL, username, password)
		try:
			response = urllib2.urlopen(call)
			parsedBody = format.read(response)
			bodyDataExtracter.setResponseCode(response.code)
			bodyDataExtracter.setParsedBody(parsedBody)
			bodyDataExtracter.setIfModifiedSinceError(self.getIfLastModifiedNo(call, response))
			bodyDataExtracter.setIfModifiedSinceSuccess(self.getIfLastModifiedYes(formattedURL, username, password))
			response.close()
		except urllib2.HTTPError, request:
			bodyDataExtracter.setResponseCode(request.code)
			request = self.getBody(formattedURL, self.username, self.password, format)
			bodyDataExtracter.setParsedBody(request)

	@_http_ise_error_logging
	def postTest(self, URL, dict='has not been set', username='has not been set',\
				password='has not been set', bodyDataExtracter='has not been set', format=NoFormat(),\
				userObject='has not been set'):

		if username == 'has not been set':
			username = self.username
		if password == 'has not been set':
			password = self.password
		if dict == 'has not been set':
			dict = self.info
		if userObject == 'has not been set':
			userObject = self.userObject
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = format.formatURL(URL)
		else:
			formattedURL = URL
		data = format.write(dict)
		call = ServerController.requests.post(formattedURL, username, password, data)
		try:
			request = urllib2.urlopen(call)
			parsedBody = format.read(request)
			bodyDataExtracter.setResponseCode(request.code)
			bodyDataExtracter.setParsedBody(parsedBody)
			request.close()
			ServerController.newID = parsedBody['ID']
		except urllib2.HTTPError, error:
			bodyDataExtracter.setResponseCode(error.code)
			request = self.getBody(formattedURL, self.username, self.password, format)
			bodyDataExtracter.setParsedBody(request, userObject)

	@_http_ise_error_logging
	def putTest(self, URL, dict='has not been set', username='has not been set',\
				password='has not been set', bodyDataExtracter='has not been set', format=NoFormat()):
		if username == 'has not been set':
			username = self.username
		if password == 'has not been set':
			password = self.password
		if dict == 'has not been set':
			dict = self.info
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = format.formatURL(URL)
		else:
			formattedURL = URL
		data = format.write(dict)
		call = ServerController.requests.put(formattedURL, data, username, password)
		try:
			request = urllib2.urlopen(call)
			parsedBody = format.read(request)
			bodyDataExtracter.setResponseCode(request.code)
			bodyDataExtracter.setParsedBody(parsedBody)
			request.close()
		except urllib2.HTTPError, error:
			bodyDataExtracter.setResponseCode(error.code)
			request = self.getBody(formattedURL, self.username, self.password, format)
			bodyDataExtracter.setParsedBody(request)

	@_http_ise_error_logging
	def deleteTest(	self, URL, username='has not been set', password='has not been set',\
					bodyDataExtracter='has not been set', format=NoFormat()):

		if username == 'has not been set':
			username = self.username
		if password == 'has not been set':
			password = self.password

		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = format.formatURL(URL)
		else:
			formattedURL = URL
		call = ServerController.requests.delete(formattedURL, username, password)
		try:
			request = urllib2.urlopen(call)
			notFound = self.getBody(URL, username, password, format)
			bodyDataExtracter.setResponseCode(request.code)
			bodyDataExtracter.setParsedBody(notFound)
			request.close()
		except urllib2.HTTPError, error:
			bodyDataExtracter.setResponseCode(error.code)
			request = self.getBody(formattedURL, self.username, self.password, format)
			bodyDataExtracter.setParsedBody(request)

	@_http_ise_error_logging
	def getIfLastModifiedNo(self, request, response):
		request.add_header(self.IF_LAST_MODIFIED_HEADER, response.headers.get(self.LAST_MODIFIED_KEY))
		try:
			result = urllib2.urlopen(request)
			result.close()
			return result.code
		except urllib2.HTTPError, error:
			return error.code

	@_http_ise_error_logging
	def getIfLastModifiedYes(self, URL, username='has not been set', password='has not been set'):
		request = ServerController.requests.get(URL, username, password)
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

	@_http_ise_error_logging
	def getLastModified(self, URL, ID='has not been set', format=NoFormat()):
		username = self.username
		password = self.password
		if ID != 'has not been set':
			URL = URL + '/' + ID
		call = ServerController.requests.get(URL, username, password)
		try:
			request = urllib2.urlopen(call)
			parsedBody = format.read(request)
			timeModified = parsedBody[self.LAST_MODIFIED_KEY]
			request.close()
			return timeModified
		except urllib2.HTTPError, request:
			return request.code

	@_http_ise_error_logging
	def getBody(self, URL, username='has not been set', password='has not been set', format=NoFormat()):
		if username == 'has not been set':
			username = self.username
		if password == 'has not been set':
			password = self.password
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = format.formatURL(URL)
		else:
			formattedURL = URL
		call = ServerController.requests.get(formattedURL, username, password)
		try:
			request = urllib2.urlopen(call)
			parsedBody = format.read(request)
			request.close()
			return parsedBody
		except urllib2.HTTPError, request:
			return request.code

	@_http_ise_error_logging
	def setUpPut(self, URL, dict='has not been set', username='has not been set',\
				password='has not been set', format=NoFormat()):

		if username == 'has not been set':
			username = self.username
		if password == 'has not been set':
			password = self.password
		if dict == 'has not been set':
			dict = self.info
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = format.formatURL(URL)
		else:
			formattedURL = URL
		data = format.write(dict)
		call = ServerController.requests.put(formattedURL, data, username, password)
		request = urllib2.urlopen(call)
		#body = format.read(request)
		request.close()
	@_http_ise_error_logging
	def setUpPost(self, URL, dict='has not been set', username='has not been set',\
				password='has not been set', format=NoFormat()):

		if username == 'has not been set':
			username = self.username
		if password == 'has not been set':
			password = self.password
		if dict == 'has not been set':
			dict = self.info

		#if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
		#	formattedURL = format.formatURL(URL)
		#else:
		#	formattedURL = URL

		data = format.write(dict)
		call = ServerController.requests.post(URL, username, password, data)
		request = urllib2.urlopen(call)
		body = format.read(request)
		request.close()
		return body['ID']

	@_http_ise_error_logging
	def tearDownDelete(	self, URL, username='has not been set',\
						password='has not been set', format=NoFormat()):

		if username == 'has not been set':
			username = self.username
		if password == 'has not been set':
			password = self.password
		if URL.find(self.FIND_FORMAT) is self.NOT_FOUND:
			formattedURL = format.formatURL(URL)
		else:
			formattedURL = URL
		call = ServerController.requests.delete(formattedURL, username, password)
		try:
			urllib2.urlopen(call)
		except urllib2.HTTPError:
			# These are all ignored during teardown.
			pass

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

