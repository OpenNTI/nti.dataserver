import os
import urllib2

from time import mktime
from wsgiref import handlers
from datetime import datetime
from servertests.generalpurpose.utilities.url_formatter import NoFormat
from servertests.generalpurpose import TestConstants

##########################

_APP_PATH = os.path.dirname( __file__ ) + '/../../main/python/app.py'
VOID_VALUE = 'has not been set'

#------------------------

class SubTestCalls(object):
	
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
		self.constants  = TestConstants()
		
	def addID(self, URL, ID=None):
		if ID is None:
			return URL
		else:
			return URL + '/' + ID

	def getIfLastModifiedNo(self, request, response):
		request.add_header(self.IF_LAST_MODIFIED_HEADER, response.headers.get(self.LAST_MODIFIED_KEY))
		try:
			result = urllib2.urlopen(request)
			result.close()
			return result.code
		except urllib2.HTTPError, error:
			return error.code

	def getIfLastModifiedYes(self, URL, username, password):
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

	def getLastModified(self, URL, constants, ID=VOID_VALUE, fmt=NoFormat()):
		
		username, password = self._get_credentials(constants)
		
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
		
		username, password = self._get_credentials(username, password)
			
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

	def setUpPut(self, URL, constants, data=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		
		data = constants.DEFAULT_INFO if data == VOID_VALUE else data
		username, password = self._get_credentials(username, password)
			
		if URL.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URL)
		else:
			formattedURL = URL
		data = fmt.write(data)
		call = self.requests.put(formattedURL, data, username, password)
		request = urllib2.urlopen(call)
		#body = fmt.read(request)
		request.close()

	def setUpPost(self, URL,constants, data=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		
		data = constants.DEFAULT_INFO if data == VOID_VALUE else data
		username, password = self._get_credentials(username, password)
		
		data = fmt.write(data)
		call = self.requests.post(URL, username, password, data)
		request = urllib2.urlopen(call)
		body = fmt.read(request)
		request.close()
		return body['ID']

	def tearDownDelete(	self, URL, constants, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		
		username, password = self._get_credentials(username, password)
			
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
				
	def _get_credentials(self, username=VOID_VALUE, password=VOID_VALUE):
		username = self.constants.username if username == VOID_VALUE else username
		password = self.constants.password if password == VOID_VALUE else password
		return (username, password)
	
class GetTest(SubTestCalls):
	
	def run(self, URL, URLGroup, data, username, password, bodyDataExtracter, fmt=NoFormat()):
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
			request = self.getBody(formattedURL, self.constants.username, self.constants.password, fmt)
			bodyDataExtracter.setParsedBody(request)
			
class PostTest(SubTestCalls):
	
	def run(self, URL, URLGroup, data, username, password, bodyDataExtracter, fmt=NoFormat()):
		
		if URLGroup.find(self.FIND_FORMAT) == self.NOT_FOUND:
			formattedURL = fmt.formatURL(URLGroup)
		else:
			formattedURL = URLGroup
			
		data = fmt.write(data)
		call = self.requests.post(formattedURL, username, password, data)
		try:
			request = urllib2.urlopen(call)
			parsedBody = fmt.read(request)
			bodyDataExtracter.setResponseCode(request.code)
			bodyDataExtracter.setParsedBody(parsedBody)
			request.close()
			bodyDataExtracter.newID = parsedBody['ID']
		except urllib2.HTTPError, error:
			bodyDataExtracter.setResponseCode(error.code)
			bodyDataExtracter.setParsedBody(self.getBody(formattedURL, self.constants.username, self.constants.password, fmt))
			
class PutTest(SubTestCalls):
	
	def run(self, URL, URLGroup, data, username, password, bodyDataExtracter, fmt=NoFormat()):
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
			request = self.getBody(formattedURL, self.constants.username, self.constants.password, fmt)
			bodyDataExtracter.setParsedBody(request)

class DeleteTest(SubTestCalls):
	
	def run(self, URL, URLGroup, data, username, password, bodyDataExtracter, fmt=NoFormat()):
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
			request = self.getBody(formattedURL, self.constants.username, self.constants.password, fmt)
			bodyDataExtracter.setParsedBody(request)

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

class PostTestExpectedError(object):

	def postException(self, body, ID):
		print body['Items'][ID]