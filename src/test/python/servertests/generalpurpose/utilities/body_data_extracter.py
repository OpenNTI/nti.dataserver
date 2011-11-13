'''
Created on Oct 10, 2011

@author: ltesti
'''
##########################
		
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
		
	def setDefaultID(self, ID):
		self.DefaultID = ID
	
class URL_DefaultV2(URLFunctionality):
	
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
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
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
		
class URL_DefaultV3_Quizzes(URLFunctionality):
	
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
			modification = ParsedBodyModifier()
			modification.removeOID(self.body)
			if isinstance(self.body, list):
				self.body = modification.extractInfo(self.body)
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
	
class URL_DefaultV3_Results(URLFunctionality):
	
	def setParsedBody(self, parsedBody):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
		self.responseCode = responseCode
	
	def setBody(self):
		try:
			self.body = self.parsedBody[self.defaultID]['Items']
			modification = ParsedBodyModifier()
			modification.removeOID(self.body)
			if isinstance(self.body, list):
				self.body = modification.extractInfo(self.body)
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
		
	def setDefaultID(self, oid):
		self.defaultID = oid
		
class URL_DefaultV3_Post(URLFunctionality):
	
	def setParsedBody(self, parsedBody):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
		self.responseCode = responseCode
	
	def setBody(self):
		try:
			self.body = self.parsedBody['TestQuiz'][self.DefaultID]['Items']
			modification = ParsedBodyModifier()
			modification.removeOID(self.body)
			if isinstance(self.body, list):
				self.body = modification.extractInfo(self.body)
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
		
class URL_PostV2(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, type(10)) == True:
			self.body = self.parsedBody
		else:
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
			self.body = self.parsedBody['PostPutKey']
	
	def setLastModified(self):
		if isinstance(self.parsedBody, type(10)) == True:
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
		if isinstance(self.parsedBody, type(10)) == True:
			self.body = self.parsedBody
		else:
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
			self.body = self.parsedBody['PostPutKey']
	
	def setLastModified(self):
		if isinstance(self.parsedBody, type(10)) == True:
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
			self.body = self.parsedBody['TestQuiz']['Items']
			modification = ParsedBodyModifier()
			modification.removeOID(self.body)
			if isinstance(self.body, list):
				self.body = modification.extractInfo(self.body)
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

class URL_Group(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, type(10)) == True:
			self.body = self.parsedBody
		else:
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
			self.body = self.parsedBody[self.DefaultID]['DefaultKey']
	
	def setLastModified(self):
		try:
			self.lastModified = self.parsedBody[self.DefaultID]['Last Modified']
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

class URL_Type(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, type(10)) == True:
			self.body = self.parsedBody
		else:
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
			self.body = self.parsedBody['TestGroup'][self.DefaultID]['DefaultKey']
	
	def setLastModified(self):
		if isinstance(self.parsedBody, type(10)) == True:
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
		
class URL_Assessment(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, type(10)) == True:
			self.body = self.parsedBody
		else:
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
			self.body = [(self.parsedBody['Items'][0]['Question']['Text'], self.parsedBody['Items'][0]['Question']['Answers'], self.parsedBody['Items'][0]['Assessment']),
						(self.parsedBody['Items'][1]['Question']['Text'], self.parsedBody['Items'][1]['Question']['Answers'], self.parsedBody['Items'][1]['Assessment'])]
	
	def setLastModified(self):
		if isinstance(self.parsedBody, type(10)) == True:
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

class URL_Skipped_Question_Assessment(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, type(10)) == True:
			self.body = self.parsedBody
		else:
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
			self.body = [(self.parsedBody['Items'][0]['Question']['Text'], self.parsedBody['Items'][0]['Question']['Answers'], self.parsedBody['Items'][0]['Assessment'])]
	
	def setLastModified(self):
		if isinstance(self.parsedBody, type(10)) == True:
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
		
class URL_Fail_Post_Assessment(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, type(10)) == True:
			self.body = self.parsedBody
		else:
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
			self.body = [(self.parsedBody[self.DefaultID]['Items'][0]['Question']['Text'], self.parsedBody[self.DefaultID]['Items'][0]['Question']['Answers'], self.parsedBody[self.DefaultID]['Items'][0]['Assessment']),
						(self.parsedBody[self.DefaultID]['Items'][1]['Question']['Text'], self.parsedBody[self.DefaultID]['Items'][1]['Question']['Answers'], self.parsedBody[self.DefaultID]['Items'][1]['Assessment'])]
	
	def setLastModified(self):
		if isinstance(self.parsedBody, type(10)) == True:
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

class URL_Delete_Group(URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		if isinstance(self.parsedBody, type(10)) == True:
			self.body = self.parsedBody
		else:
			modification = ParsedBodyModifier()
			modification.removeOID(self.parsedBody)
			self.body = [(self.parsedBody['TestQuiz'][self.DefaultID]['Items'][0]['Question']['Text'], self.parsedBody['TestQuiz'][self.DefaultID]['Items'][0]['Question']['Answers'], self.parsedBody['TestQuiz'][self.DefaultID]['Items'][0]['Assessment']),
						(self.parsedBody['TestQuiz'][self.DefaultID]['Items'][1]['Question']['Text'], self.parsedBody['TestQuiz'][self.DefaultID]['Items'][1]['Question']['Answers'], self.parsedBody['TestQuiz'][self.DefaultID]['Items'][1]['Assessment'])]
	
	def setLastModified(self):
		if isinstance(self.parsedBody, type(10)) == True:
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

class ParsedBodyModifier(object):

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
		
	def extractInfo(self, body):
		storedInfo = []
		for result in body:
			question 	= result['Question']['Text']
			answer		= result['Question']['Answers']
			assessment 	= result['Assessment']
			storedInfo.append((question, answer, assessment))
		return storedInfo
			
