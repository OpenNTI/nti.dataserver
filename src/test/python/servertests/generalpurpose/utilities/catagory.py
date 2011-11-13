'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose.utilities.server_call_type import SubTestCalls
from servertests.generalpurpose import V2Constants
from servertests.generalpurpose import V3Constants_Quizzes
from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.utilities.url_formatter import PlistFormat
from servertests.generalpurpose.utilities import body_data_extracter
import uuid

class ServerTesting(object):
	
	VOID_VALUE = 'not set'
	
	def getTest(self): pass
	
	def postTest(self, url):
		return url + '/' + self.SetUpPostID
	
	def putTest(self): pass
	
	def deleteTest(self): pass
	
class ServerTestV2(ServerTesting):

	def getTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV2()
		else:
			self.bodyDataExtracter = bodyExtracter
		self.bodyDataExtracter.setDefaultID(self.SetUpPostID)
		return (self.constants.URL_USER_NO_FORMAT, self.constants.URL_USER_POST, self.constants.POST_PUT_INFO, self.constants, self.bodyDataExtracter)
	
	def postTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_PostV2()
		else:
			self.bodyDataExtracter = bodyExtracter
		self.bodyDataExtracter.setDefaultID(self.SetUpPostID)
		return (self.constants.URL_USER_POST, self.constants.URL_USER_POST, self.constants.POST_PUT_INFO, self.constants, self.bodyDataExtracter)
	
	def putTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_PostV2()
		else:
			self.bodyDataExtracter = bodyExtracter
		self.bodyDataExtracter.setDefaultID(self.SetUpPostID)
		return (self.constants.URL_USER_NO_FORMAT, self.constants.URL_USER_POST, self.constants.POST_PUT_INFO, self.constants, self.bodyDataExtracter)
	
	def deleteTest(self, bodyExtracter): 
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV2()
		else:
			self.bodyDataExtracter = bodyExtracter
		self.bodyDataExtracter.setDefaultID(self.SetUpPostID)
		return (self.constants.URL_USER_NO_FORMAT, self.constants.URL_USER_POST, self.constants.POST_PUT_INFO, self.constants, self.bodyDataExtracter)
	
	def setUp(self, constants):
		# a set of puts and deletes that are set before each test
		UUID = str(uuid.uuid4())
		self.constants = V2Constants(UUID)
		self.tester                  = SubTestCalls()
		self.tester.setUpPut(constants.URL_USER_NO_FORMAT, constants)
		self.tester.setUpPut(constants.URL_USER_NO_FORMAT, constants, fmt=PlistFormat())
		self.tester.setUpPut(constants.URL_OTHER_USER_NO_FORMAT, constants, username=constants.otherUser)
		self.NoFormat_resp_ID = self.tester.setUpPost(constants.URL_USER_POST, constants, data=constants.DEFAULT_INFO)
		self.NoFormat_resp_ID_old = self.NoFormat_resp_ID
		self.NoFormat_resp_ID = self.tester.setUpPost(constants.URL_USER_POST, constants, data=constants.DEFAULT_INFO)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_POST, self.NoFormat_resp_ID_old), constants)
		self.SetUpPostID        = self.tester.setUpPost(constants.URL_USER_POST, constants)
		self.JunkGroupIDURL		= constants.URL_USER + '/ltesti/' + str(uuid.uuid4()) + '/TestGroup1/' + self.SetUpPostID
		self.TypeGroupIDURL		= constants.URL_USER + '/ltesti/TestType1/TestGroup1/' + self.SetUpPostID
		return (self.NoFormat_resp_ID_old, self.NoFormat_resp_ID)
		
	def tearDown(self, constants):
		try:
			if hasattr(self.bodyDataExtracter, "DefaultID") is False: self.bodyDataExtracter.DefaultID = None
		except AttributeError: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV2()
			self.bodyDataExtracter.DefaultID = None
		self.tester.tearDownDelete(constants.URL_USER_NO_FORMAT, constants)
		self.tester.tearDownDelete(constants.URL_OTHER_USER_NO_FORMAT, constants, username=constants.otherUser)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_POST, self.SetUpPostID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_POST, self.bodyDataExtracter.DefaultID), constants)
		self.tester.tearDownDelete(constants.URL_USER_NONEXIST_TYPE, constants)
		self.tester.tearDownDelete(constants.URL_USER_NONEXIST_GROUP, constants)
		self.tester.tearDownDelete(constants.URL_USER_NONEXIST_ID, constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_NONEXIST_TYPE_NO_ID, self.bodyDataExtracter.DefaultID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_NONEXIST_GROUP_NO_ID, self.bodyDataExtracter.DefaultID), constants)
	
class ServerTestV3_quizzes(ServerTesting):
	
	def getTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV3_Quizzes()
		else:
			self.bodyDataExtracter = bodyExtracter
		return (self.constants.URL_NO_FORMAT, self.constants.URL_POST, self.constants.POST_PUT_INFO, self.constants, self.bodyDataExtracter)
	
	def postTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV3_Quizzes()
		else:
			self.bodyDataExtracter = bodyExtracter
		return (self.constants.URL_POST, self.constants.URL_NO_FORMAT, self.constants.POST_PUT_INFO, self.constants, self.bodyDataExtracter)
	
	def putTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV3_Quizzes()
		else:
			self.bodyDataExtracter = bodyExtracter
		return (self.constants.URL_NO_FORMAT, self.constants.URL_POST, self.constants.POST_PUT_INFO, self.constants, self.bodyDataExtracter)
	
	def deleteTest(self, bodyExtracter): 
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV3_Quizzes()
		else:
			self.bodyDataExtracter = bodyExtracter
		return (self.constants.URL_NO_FORMAT, self.constants.URL_POST, self.constants.POST_PUT_INFO, self.constants, self.bodyDataExtracter)
	
	def setUp(self, constants):
		self.constants = V3Constants_Quizzes()
		self.tester               = SubTestCalls()
		self.tester.setUpPut(constants.URL_NO_FORMAT, constants)
		self.tester.setUpPut(constants.URL_MATH_XML, constants, constants.DEFAULT_INFO_OPEN_MATH_XML_INFO)
		self.URL_NoID   = self.tester.addID(constants.URL_POST, str(uuid.uuid4()))
		self.URL_nonExsitsQuiz = self.tester.addID(constants.URL, str(uuid.uuid4()))
	
	def tearDown(self, constants):
		self.tester.tearDownDelete(constants.URL_NO_FORMAT, constants)
		self.tester.tearDownDelete(constants.URL_MATH_XML, constants)
		self.tester.tearDownDelete(self.URL_NoID, constants)
	
class ServerTestV3_results(ServerTesting):
	
	def getTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV3_Results()
		else:
			self.bodyDataExtracter = bodyExtracter
		self.constants = V3Constants_Results(body_data_extracter)
		self.bodyDataExtracter.setDefaultID(self.NoFormat_resp_ID)
		return (self.constants.URL_USER_NO_FORMAT, self.constants.URL_USER_POST, self.constants.DEFAULT_INFO, self.constants, self.bodyDataExtracter)
	
	def postTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_Assessment()
		else:
			self.bodyDataExtracter = bodyExtracter
		self.constants = V3Constants_Results()
		self.bodyDataExtracter.setDefaultID(self.NoFormat_resp_ID)
		return (self.constants.URL_USER_NO_FORMAT, self.constants.URL_USER_NO_FORMAT, self.constants.DEFAULT_INFO, self.constants, self.bodyDataExtracter)
	
	def putTest(self, bodyExtracter):
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV3_Results()
		else:
			self.bodyDataExtracter = bodyExtracter
		self.constants = V3Constants_Results()
		self.bodyDataExtracter.setDefaultID(self.NoFormat_resp_ID)
		return (self.constants.URL_USER_NO_FORMAT, self.constants.URL_USER_POST, self.constants.DEFAULT_INFO, self.constants, self.bodyDataExtracter)
	
	def deleteTest(self, bodyExtracter): 
		if bodyExtracter == self.VOID_VALUE: 
			self.bodyDataExtracter = body_data_extracter.URL_Assessment()
		else:
			self.bodyDataExtracter = bodyExtracter
		self.constants = V3Constants_Results()
		self.bodyDataExtracter.setDefaultID(self.NoFormat_resp_ID)
		return (self.URL_USER_NO_FORMAT_DELETE, self.constants.URL_USER_NO_FORMAT, self.constants.DEFAULT_INFO, self.constants, self.bodyDataExtracter)
	
	def setUp(self, constants):
		self.tester               = SubTestCalls()
		try:
			if hasattr(self.bodyDataExtracter, "DefaultID") is False: self.bodyDataExtracter.DefaultID = None
		except AttributeError: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV2()
			self.bodyDataExtracter.DefaultID = None
		self.tester.setUpPut(constants.URL_SETUP_FORMAT, constants, constants.SETUP_INFO)
		self.tester.setUpPut(constants.URL_SETUP_MATH_XML, constants, data=constants.SETUP_MATH_XML)
		self.NoFormat_resp_ID = self.tester.setUpPost(constants.URL_USER_NO_FORMAT, constants, data=constants.DEFAULT_INFO)
		self.NoFormat_resp_ID_old = self.NoFormat_resp_ID
		self.NoFormat_resp_ID = self.tester.setUpPost(constants.URL_USER_NO_FORMAT, constants, data=constants.DEFAULT_INFO)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_NO_FORMAT, self.NoFormat_resp_ID_old), constants)
		self.Other_resp_ID = self.tester.setUpPost(constants.URL_OTHER_USER_NO_FORMAT, constants, data=constants.DEFAULT_INFO, 
																		username=constants.otherUser)
		self.URL_NON_EXIST_ID = self.tester.addID(constants.URL_USER_NO_FORMAT, str(uuid.uuid4()))
		self.URL_USER_NO_FORMAT_DELETE = constants.URL_USER_NO_FORMAT + '/' + self.NoFormat_resp_ID
		return (self.NoFormat_resp_ID_old, self.NoFormat_resp_ID)
	
	def tearDown(self, constants):
		try:
			if hasattr(self.bodyDataExtracter, "DefaultID") is False: self.bodyDataExtracter.DefaultID = None
		except AttributeError: 
			self.bodyDataExtracter = body_data_extracter.URL_DefaultV2()
			self.bodyDataExtracter.DefaultID = None
		self.tester.tearDownDelete(constants.URL_SETUP_FORMAT, constants)
		self.tester.tearDownDelete(constants.URL_SETUP_MATH_XML, constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_NO_FORMAT, self.NoFormat_resp_ID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_NO_FORMAT, self.Other_resp_ID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_NO_FORMAT, self.bodyDataExtracter.DefaultID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_MATH_XML, self.NoFormat_resp_ID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_MATH_XML, self.bodyDataExtracter.DefaultID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_OTHER_USER_NO_FORMAT, self.bodyDataExtracter.DefaultID), constants, 
												username=constants.otherUser)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_NO_FORMAT, self.NoFormat_resp_ID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_USER_MATH_XML, self.NoFormat_resp_ID), constants)
		self.tester.tearDownDelete(self.tester.addID(constants.URL_OTHER_USER_NO_FORMAT, self.Other_resp_ID), constants, 
												username=constants.otherUser)
	
class ServerTestV4(ServerTesting):
	
	def getTest(self): pass
	
	def postTest(self): pass
	
	def putTest(self): pass
	
	def deleteTest(self): pass
	
	def setUp(self): pass
	
	def tearDown(self): pass
