from servertests.control import UserObject
from servertests.control import OID_Remover
from servertests.control import URLFunctionality
	
##########################
		
class URL_Default(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		try:
			self.body = self.parsedBody['Items']
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.body)
		except (KeyError, TypeError):
			self.body = self.parsedBody
	
	def setLastModified(self):
		try:
			self.lastModified = self.parsedBody['Last Modified']
		except (KeyError, TypeError):
			self.lastModified = self.parsedBody
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess
	
class URL_QuizGroup(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.userObject = userObject
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
		self.responseCode = responseCode
	
	def setBody(self):
		try:
			self.body = self.parsedBody['First_quiz']['Items']
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.body)
		except (KeyError, TypeError):
			self.body = self.parsedBody
	
	def setLastModified(self):
		try:
			self.lastModified = self.parsedBody['Last Modified']
		except (KeyError, TypeError):
			self.lastModified = self.parsedBody
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess
	
class URL_IDExtracter(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.userObject = userObject or UserObject()
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
		self.responseCode = responseCode
	
	def setBody(self):
		ID = self.userObject.getUserID()
		try:
			self.body = self.parsedBody[ID]['Items']
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.body)
		except (KeyError, TypeError):
			self.body = self.parsedBody
		
	def setLastModified(self):
		try:
			self.lastModified = self.parsedBody['Last Modified']
		except (KeyError, TypeError):
			self.lastModified = self.parsedBody

	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess

class OID_Remover(object):

	def removeOID(self, body):
		if isinstance(body, list):
			for index in body:
				if isinstance(index, dict or list):
					self.removeOID(index)
		elif isinstance(body, dict):
			keys = body.keys()
			for key in keys:
				if isinstance(body[key], dict or list):
					self.removeOID(body[key])
		try:		
			del body['OID']
		except (KeyError, TypeError):
			pass
		try:
			del body["Creator"]
		except (KeyError, TypeError):
			pass
