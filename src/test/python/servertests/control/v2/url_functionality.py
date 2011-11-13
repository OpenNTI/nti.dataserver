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
		if isinstance(self.parsedBody, int):
			self.body = self.parsedBody
		else:
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['DefaultKey']
	
	def setLastModified(self):
		if isinstance(self.parsedBody, int):
			self.lastModified = self.parsedBody
		else:
			self.lastModified = self.parsedBody['Last Modified']
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess

class URL_Group(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, int):
			self.body = self.parsedBody
		else:
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['jsonID']['DefaultKey']
	
	def setLastModified(self):
		try:
			self.lastModified = self.parsedBody['jsonID']['Last Modified']
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
	
class URL_TypeGet(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
		self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, int):
			self.body = self.parsedBody
		else:
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['TestGroup']['jsonID']['DefaultKey']
	
	def setLastModified(self):
		if isinstance(self.parsedBody, int):
			self.lastModified = self.parsedBody
		else:
			self.lastModified = self.parsedBody['Last Modified']
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess

class URL_Create(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, int):
			self.body = self.parsedBody
		else:
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['PostPutKey']
	
	def setLastModified(self):
		if isinstance(self.parsedBody, int):
			self.lastModified = self.parsedBody
		else:
			self.lastModified = self.parsedBody['Last Modified']
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess
		
class URL_Successful_Put_Response(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, int):
			self.body = self.parsedBody
		else:
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['PostPutKey']
	
	def setLastModified(self):
		if isinstance(self.parsedBody, int):
			self.lastModified = self.parsedBody
		else:
			self.lastModified = self.parsedBody['Last Modified']
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except KeyError:
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess
		
class URL_oldGroup_json(URLFunctionality):
		
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
		self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, int):
			self.body = self.parsedBody
		else:
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['jsonID']['DefaultKey']
	
	def setLastModified(self):
		if isinstance(self.parsedBody, int):
			self.lastModified = self.parsedBody
		else:
			self.lastModified = self.parsedBody['Last Modified']
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess

class URL_oldGroup_plist(URLFunctionality):
	
	def getBody(self, parsedBody):
		return parsedBody['plistID']['DefaultKey']
	
	def getLastModified(self, parsedBody):
		pass
	
	def getID(self, parsedBody):
		pass
