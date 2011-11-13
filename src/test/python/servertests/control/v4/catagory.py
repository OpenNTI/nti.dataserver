'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.control.v4 import ServerControl
from servertests.control import v4
from servertests.control.v4 import bodyDataExtracter
from servertests.control.v4.URLFormatter import PlistFormat
import time
import uuid

class ServerTesting(object):
	
	def standardTest(self): pass
	
	def groupTest(self): pass
	
	def typeTest(self): pass
	
	def jsonTest(self): pass
	
	def plistTest(self): pass
	
	def unauthorizedTest(self): pass
	
	def nonExist(self): pass
	
class ServerTestV2(ServerTesting):

	def standardTest(self):
		constants = v4.V2Constants()
		self.bodyExtracter = bodyDataExtracter.URL_DefaultV2()
		return (constants.URL_JSON, constants.DEFAULT_INFO, constants, self.bodyExtracter)
	
	def groupTest(self): pass
	
	def typeTest(self): pass
	
	def jsonTest(self): pass
	
	def plistTest(self): pass
	
	def unauthorizedTest(self): pass
	
	def nonExist(self): pass
			
#	def tearDownData(self):
#		tester = self.controller()
#		tester.tearDownDelete(self.URL_json)
#		tester.tearDownDelete(self.URL_plist)
#		tester.tearDownDelete(self.URL_other_put, username=self.otherUser)
#		tester.tearDownDelete(tester.addID(self.URL_post, tester.newID))
#		tester.tearDownDelete(self.NoTypeWithID)
#		tester.tearDownDelete(self.NoGroupWithID)
#		tester.tearDownDelete(self.NoID)
#		tester.tearDownDelete(tester.addID(self.NoTypeNoID, tester.newID))
#		tester.tearDownDelete(tester.addID(self.NoGroupNoID, tester.newID))
	
	def setUp(self, constants):
		
		# a set of puts and deletes that are set before each test
		self.NoTypeGroup		= constants.URL_USERS 	+ '/ltesti/' + str(uuid.uuid4()) + '/TestGroup'
		self.NoTypeWithID		= self.NoTypeGroup	+ '/TestID'
		self.NoGroupGroup		= constants.URL_USERS	+ '/ltesti/TestType/' + str(uuid.uuid4())
		self.NoGroupWithID		= self.NoGroupGroup + '/TestID'
		self.NoID				= constants.URL_USERS 	+ '/ltesti/TestType/TestGroup/' + str(uuid.uuid4())
		self.NoTypeNoID			= constants.URL_USERS	+ '/ltesti/' + str(uuid.uuid4()) + '/TestGroup'
		self.NoGroupNoID		= constants.URL_USERS	+ '/ltesti/TestType/' + str(uuid.uuid4())
		self.TypeGroupURL		= constants.URL_USERS	+ '/ltesti/TestType1/TestGroup1/'
		testerPut = ServerControl.SetUpPut()
		testerPost = ServerControl.SetUpPost()
		testerPut.setUpPut(constants.URL_JSON, constants)
		testerPut.setUpPut(constants.URL_PLIST, constants, fmt=PlistFormat())
		testerPut.setUpPut(constants.URL_OTHER_PUT, constants, username=constants.otherUser)
		self.SetUpPostID = testerPost.setUpPost(self.TypeGroupURL, constants)
		self.JunkGroupIDURL		= constants.URL_USERS	+ '/ltesti/' + str(uuid.uuid4()) + '/TestGroup1/' + self.SetUpPostID
		self.TypeGroupIDURL		= constants.URL_USERS	+ '/ltesti/TestType1/TestGroup1/' + self.SetUpPostID
	
class ServerTestV3_quizzes(object):
	
	def standardTest(self): pass
	
	def groupTest(self): pass
	
	def typeTest(self): pass
	
	def jsonTest(self): pass
	
	def plistTest(self): pass
	
	def unauthorizedTest(self): pass
	
	def nonExist(self): pass
	
	def setUp(self): pass
	
	def tearDown(self): pass
	
class ServerTestV3_response(object):
	
	def standardTest(self): pass
	
	def groupTest(self): pass
	
	def typeTest(self): pass
	
	def jsonTest(self): pass
	
	def plistTest(self): pass
	
	def unauthorizedTest(self): pass
	
	def nonExist(self): pass
	
	def setUp(self): pass
	
	def tearDown(self): pass
	
class ServerTestV4(object):
	
	def standardTest(self): pass
	
	def groupTest(self): pass
	
	def typeTest(self): pass
	
	def jsonTest(self): pass
	
	def plistTest(self): pass
	
	def unauthorizedTest(self): pass
	
	def nonExist(self): pass
	
	def setUp(self): pass
	
	def tearDown(self): pass
