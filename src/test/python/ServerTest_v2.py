import uuid
import time
import unittest

import ServerControl
from servertests import DataServerTestCase

class URL_Default(ServerControl.URLFunctionality):

	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()

	def setResponseCode(self, responseCode):
		self.responseCode = responseCode

	def setBody(self):
		if isinstance(self.parsedBody, int) == True:
			self.body = self.parsedBody
		else:
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['DefaultKey']

	def setLastModified(self):
		if isinstance(self.parsedBody, int) == True:
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

class URL_Group(ServerControl.URLFunctionality):

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

class URL_TypeGet(ServerControl.URLFunctionality):

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
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['TestGroup']['jsonID']['DefaultKey']

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

class URL_Create(ServerControl.URLFunctionality):

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
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
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

class URL_Successful_Put_Response(ServerControl.URLFunctionality):

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
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
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

class URL_oldGroup_json(ServerControl.URLFunctionality):

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
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.parsedBody)
			self.body = self.parsedBody['jsonID']['DefaultKey']

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

class URL_oldGroup_plist(ServerControl.URLFunctionality):

	def getBody(self, parsedBody):
		return parsedBody['plistID']['DefaultKey']

	def getLastModified(self, parsedBody):
		pass

	def getID(self, parsedBody):
		pass

class Set_ltesti_ID(object):

	def setID(self, ID):
		Set_ltesti_ID.ID = ID

	def getID(self):
		return Set_ltesti_ID.ID

class Set_sjohnson_ID(object):

	def setID(self, ID):
		Set_sjohnson_ID.ID = ID

	def getID(self):
		return Set_sjohnson_ID.ID

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

class ServerTests_v2(object):

	def constants(self):
		self.URL				  = "http://localhost:8080"
		self.URL_DS				  = self.URL 	+ '/dataserver'
		self.URL_TYPE             = self.URL_DS + '/users/ltesti@nextthought.com/TestType'
		self.URL_POST			  = self.URL_DS + '/users/ltesti@nextthought.com/TestType/TestGroup'
		self.URL_JSON			  = self.URL_DS + '/users/ltesti@nextthought.com/TestType/TestGroup/jsonID'
		self.URL_PLIST			  = self.URL_DS + '/users/ltesti@nextthought.com/TestType/TestGroup/plistID'
		self.URL_OTHER_POST	      = self.URL_DS + '/users/sjohnson@nextthought.com/TestType/TestGroup'
		self.URL_OTHER_PUT		  = self.URL_DS + '/users/sjohnson@nextthought.com/TestType/TestGroup/TestID'
		self.NON_EXSIST_TYPE_URL  = self.URL_DS + '/users/ltesti@nextthought.com/doesNotExist/TestGroup/TestID'
		self.NON_EXSIST_GROUP_URL = self.URL_DS + '/users/ltesti@nextthought.com/TestType/doesNotExist/TestID'
		self.NON_EXSIST_ID_URL	  = self.URL_DS + '/users/ltesti@nextthought.com/TestType/TestGroup/doesNotExist'
		self.DEFAULT_INFO		  = {"DefaultKey":"StartingInfo"}
		self.POST_PUT_INFO		  = {"PostPutKey":"NewInfo"}
		self.DEFAULT_RETURN_KEY   = 'DefaultKey'
		self.POST_PUT_RETURN_KEY  = 'PostPutKey'
		self.DEFAULT_RETURN	      = 'StartingInfo'
		self.POST_PUT_RETURN	  = 'NewInfo'
		self.INCORRECT_USER_PASS  = 'incorrect@nextthought.com'
		self.EMPTY_USER_PASS	  = ''
		self.NO_USER_PASS		  = None

class ServerTests(DataServerTestCase):

	@classmethod
	def setUpClass(cls):

#		******************************
#		*** Default inputs Section ***
#		******************************

		constants						= ServerTests_v2()
		constants.constants()

		ServerTests.URL_type			= constants.URL_TYPE
		ServerTests.URL_post		    = constants.URL_POST
		ServerTests.URL_json		    = constants.URL_JSON
		ServerTests.URL_plist		  	= constants.URL_PLIST
		ServerTests.URL_other_post	  	= constants.URL_OTHER_POST
		ServerTests.URL_other_put	  	= constants.URL_OTHER_PUT
		ServerTests.NonExsistTypeURL	= constants.NON_EXSIST_TYPE_URL
		ServerTests.NonExsistGroupURL	= constants.NON_EXSIST_GROUP_URL
		ServerTests.NonExsistID_URL		= constants.NON_EXSIST_ID_URL
		ServerTests.default_info		= constants.DEFAULT_INFO
		ServerTests.postPut_info		= constants.POST_PUT_INFO
		ServerTests.default_returnKey	= constants.DEFAULT_RETURN_KEY
		ServerTests.postPut_returnKey	= constants.POST_PUT_RETURN_KEY
		ServerTests.default_return		= constants.DEFAULT_RETURN
		ServerTests.postPut_return		= constants.POST_PUT_RETURN
		ServerTests.incorrectUser		= constants.INCORRECT_USER_PASS
		ServerTests.incorrectPassword	= constants.INCORRECT_USER_PASS
		ServerTests.emptyUser			= constants.EMPTY_USER_PASS
		ServerTests.emptyPassword		= constants.EMPTY_USER_PASS
		ServerTests.noUser				= constants.NO_USER_PASS
		ServerTests.noPassword			= constants.NO_USER_PASS

		defaults						= ServerControl.DefaultValues()
		ServerTests.path				= defaults.path
		ServerTests.username			= defaults.username
		ServerTests.otherUser			= defaults.otherUser
		ServerTests.password			= defaults.password
		ServerTests.incorrectPassword	= defaults.incorrectpassword
		ServerTests.message				= defaults.message
		ServerTests.void				= defaults.void
		ServerTests.TinyNumber			= defaults.TinyNumber
		ServerTests.LonelyNumber		= defaults.LonelyNumber
		ServerTests.TheNumberTwo		= defaults.TheNumberTwo
		ServerTests.TheNumberThree		= defaults.TheNumberThree
		ServerTests.OK					= defaults.OK
		ServerTests.SuccessfulAdd		= defaults.SuccessfulAdd
		ServerTests.SuccessfulDelete	= defaults.SuccessfulDelete
		ServerTests.NotModifiedSince	= defaults.NotModifiedSince
		ServerTests.Unauthorized		= defaults.Unauthorized
		ServerTests.Forbidden			= defaults.Forbidden
		ServerTests.NotFound			= defaults.NotFound
		ServerTests.NotAllowed			= defaults.NotAllowed
		ServerTests.WrongType			= defaults.WrongType

		ServerTests.ID_ltesti			= Set_ltesti_ID()
		ServerTests.ID_sjohnson			= Set_sjohnson_ID()
		ServerTests.json				= ServerControl.JsonFormat()
		ServerTests.plist				= ServerControl.PlistFormat()
		ServerTests.noFormat			= ServerControl.NoFormat()
		ServerTests.tester				= ServerControl.ServerController()
		ServerTests.test				= ServerControl.PostTest()
		ServerTests.json_oldGroup		= URL_oldGroup_json()
		ServerTests.plist_oldGroup		= URL_oldGroup_plist()

		DataServerTestCase.setUpClass()

	@classmethod
	def controller(cls):
		return cls.tester

	@classmethod
	def tearDownClass(cls):

		DataServerTestCase.tearDownClass()

	def setUp(self):
		super(ServerTests, self).setUp()
		self.LIST_NAME='TestFriendsList-%s@nextthought.com' % time.time()

#	   a set of puts and deletes that are set before each test
		self.setDefaults(ServerTests.tester)
		ServerTests.tester.setUpPut(ServerTests.URL_json)
		ServerTests.tester.setUpPut(ServerTests.URL_plist, format=ServerTests.plist)
		ServerTests.tester.setUpPut(ServerTests.URL_other_put, username=ServerTests.otherUser, format=ServerTests.json)

		ServerTests.NoTypeGroup	  = 'http://localhost:8080/dataserver/users/ltesti@nextthought.com/' + str(uuid.uuid4()) + '/TestGroup'
		ServerTests.NoTypeWithID	  = ServerTests.NoTypeGroup + '/TestID'
		ServerTests.NoGroupGroup	  = 'http://localhost:8080/dataserver/users/ltesti@nextthought.com/TestType/' + str(uuid.uuid4())
		ServerTests.NoGroupWithID  =	ServerTests.NoGroupGroup + '/TestID'
		ServerTests.NoID			  = 'http://localhost:8080/dataserver/users/ltesti@nextthought.com/TestType/TestGroup/' + str(uuid.uuid4())
		ServerTests.NoTypeNoID	  = 'http://localhost:8080/dataserver/users/ltesti@nextthought.com/' + str(uuid.uuid4()) + '/TestGroup'
		ServerTests.NoGroupNoID	  = 'http://localhost:8080/dataserver/users/ltesti@nextthought.com/TestType/' + str(uuid.uuid4())
		ServerTests.TypeGroupURL = 'http://localhost:8080/dataserver/users/ltesti@nextthought.com/TestType1/TestGroup1/'
		ServerTests.SetUpPostID    = ServerTests.tester.setUpPost(ServerTests.TypeGroupURL, format=ServerTests.json)
		ServerTests.JunkGroupIDURL = 'http://localhost:8080/dataserver/users/ltesti@nextthought.com/' + str(uuid.uuid4()) + '/TestGroup1/' + ServerTests.SetUpPostID
		ServerTests.TypeGroupIDURL = 'http://localhost:8080/dataserver/users/ltesti@nextthought.com/TestType1/TestGroup1/' + ServerTests.SetUpPostID

	def tearDown(self):
		ServerTests.tester.tearDownDelete(ServerTests.URL_json)
		ServerTests.tester.tearDownDelete(ServerTests.URL_plist)
		ServerTests.tester.tearDownDelete(ServerTests.URL_other_put, username=ServerTests.otherUser)
		ServerTests.tester.tearDownDelete(ServerTests.tester.addID(ServerTests.URL_post, ServerTests.tester.newID))
		ServerTests.tester.tearDownDelete(ServerTests.NoTypeWithID)
		ServerTests.tester.tearDownDelete(ServerTests.NoGroupWithID)
		ServerTests.tester.tearDownDelete(ServerTests.NoID)
		ServerTests.tester.tearDownDelete(ServerTests.tester.addID(ServerTests.NoTypeNoID, ServerTests.tester.newID))
		ServerTests.tester.tearDownDelete(ServerTests.tester.addID(ServerTests.NoGroupNoID, ServerTests.tester.newID))

#	********************
#	*** Set Defaults ***
#	********************

	def setDefaults(self, obj):
		obj.create(ServerTests.username, ServerTests.password, ServerTests.default_info, ServerTests.ID_ltesti)

	#-----------------------------------
#		*********************************
#		*** Simple one-variable Tests ***
#		*********************************

#		*************
#		* Get tests *
#		*************

	#-----------------------------------

	def test_Server200DefaultGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.default_return, lastModified=modifiedTime,
								ifModifiedSinceError=ServerTests.NotModifiedSince, ifModifiedSinceSuccess=ServerTests.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '1'

	def test_Server200GroupGetTestCase(self):
		bodyDataExtracter = URL_Group()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_post, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.default_return, lastModified=modifiedTime,
								ifModifiedSinceError=ServerTests.NotModifiedSince, ifModifiedSinceSuccess=ServerTests.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertLessEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')

	def test_Server200TypeGetTestCase(self):
#		pdb.set_trace()
		bodyDataExtracter = URL_TypeGet()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_type, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_type)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.default_return, lastModified=modifiedTime,
								ifModifiedSinceError=ServerTests.NotModifiedSince, ifModifiedSinceSuccess=ServerTests.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertLessEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, (bodyDataExtracter.ifModifiedSinceSuccess, \
																expectedValues.ifModifiedSinceSuccess, ' If-Modified_Since result supposed to be 200'))

	def test_Server200JsonFormatGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.default_return, lastModified=modifiedTime,
								ifModifiedSinceError=ServerTests.NotModifiedSince, ifModifiedSinceSuccess=ServerTests.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '2'

	def test_Server200PlistFormatGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_plist, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.default_return, lastModified=modifiedTime,
								ifModifiedSinceError=ServerTests.NotModifiedSince, ifModifiedSinceSuccess=ServerTests.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '3'

	@unittest.skip("cannot detect an incorrect Username")
	def test_Server401IncorrectUsernameGetTestCaseSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.void, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read from URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print 'A'

	def test_Server200IncorrectUsernameGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.default_return, lastModified=modifiedTime,
								ifModifiedSinceError=ServerTests.NotModifiedSince, ifModifiedSinceSuccess=ServerTests.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '4'

	def test_Server401EmptyUsernameGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, username=ServerTests.emptyUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.void, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read from URL')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		#print '5'

	@unittest.skip("cannot detect the lack of a username")
	def test_Server401NoUsernameGetTestCaseSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.void, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read from URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print 'B'

	@unittest.expectedFailure
	def test_Server200NoUsernameGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.default_return, lastModified=modifiedTime,
								ifModifiedSinceError=ServerTests.NotModifiedSince, ifModifiedSinceSuccess=ServerTests.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '6'

	def test_Server401IncorrectPasswordGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read from URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		#print '7'

	def test_Server401EmptyPasswordGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, password=ServerTests.emptyPassword, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read from URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		#print '8'

	def test_Server401NoPasswordGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, password=ServerTests.void, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read from URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		#print '9'

	def test_Server200OtherPersonsPathGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.URL_json, username=ServerTests.otherUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.default_return, lastModified=modifiedTime,
								ifModifiedSinceError=ServerTests.NotModifiedSince, ifModifiedSinceSuccess=ServerTests.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL to read from")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '10'

	def test_Server404NonExsistantTypeGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.NonExsistTypeURL, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.NonExsistTypeURL)
		expectedValues.setValues(code=ServerTests.NotFound, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found to read from')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		#print '11'

	def test_Server404NonExsistantGroupGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.NonExsistGroupURL, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.NonExsistGroupURL)
		expectedValues.setValues(code=ServerTests.NotFound, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found to read from')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		#print '12'

	def test_Server404NonExsistantIDGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		tester.getTest(ServerTests.NonExsistID_URL, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.NonExsistID_URL)
		expectedValues.setValues(code=ServerTests.NotFound, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found to read from')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		#print '13'

	#-----------------------------------

#		**************
#		* Post Tests *
#		**************

	#-----------------------------------

	def test_Server201DefaultPostTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_post, ID=bodyDataExtracter.id)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'oldGroupTime unexpectedly greater than modifiedTimeGrp')
		self.assertRaises(KeyError, ServerTests.test.postException, oldGroup, bodyDataExtracter.id)
		#print '14'

	def test_Server201JsonFormatPostTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)

		ServerTests.tester.getBody(ServerTests.URL_post)
		ServerTests.tester.getLastModified(ServerTests.URL_post)

		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_post, ID=bodyDataExtracter.id)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		#print '15'

	@unittest.skip("does not detect an incorrect username")
	def test_Server401JsonFormatIncorrectUsernamePostSkipped(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print 'C'

	def test_Server403JsonFormatIncorrectUsernamePostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode)
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print '16'

	@unittest.expectedFailure
	def test_Server500JsonFormatEmptyUsernamePostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.emptyUser, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print '17'

	@unittest.skip('cannot detect the lack of a username')
	def test_Server401JsonFormatNoUsernamePostSkipped(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print 'D'

	def test_Server403JsonFormatNoUsernamePostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print '18'

	def test_Server401JsonFormatIncorrectPasswordPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print '19'

	def test_Server401JsonFormatEmptyPasswordPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print '20'

	def test_Server401JsonFormatNoPasswordPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, password=ServerTests.emptyPassword, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print '21'

	def test_Server403JsonFormatOtherPersonsPathPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.otherUser, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print '22'

	def test_Server201JsonFormatNonExsistantTypePostTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.NoTypeNoID)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.NoTypeNoID)
		tester.postTest(ServerTests.NoTypeNoID, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoTypeNoID, ID=bodyDataExtracter.id)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.NoTypeNoID)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Group time should have changed')
		self.assertRaises(TypeError, ServerTests.test.postException, oldGroup)
		#print '23'

	def test_Server201JsonFormatNonExsistantGroupPostTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.NoGroupNoID)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.NoGroupNoID)
		tester.postTest(ServerTests.NoGroupNoID, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoGroupNoID, ID=bodyDataExtracter.id)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.NoGroupNoID)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Group time should have changed')
		self.assertRaises(TypeError, ServerTests.test.postException, oldGroup, bodyDataExtracter.id)
		#print '24'

	def test_Server500JsonFormatWrongDatatypePostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, dict=ServerTests.WrongType, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		#print '25'

	#-----------------------------------

	def test_Server201PlistFormatPostTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_post, ID=bodyDataExtracter.id)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'oldGroupTime unexpectedly greater than modifiedTimeGrp')
		self.assertRaises(KeyError, ServerTests.test.postException, oldGroup, bodyDataExtracter.id)
		#print '26'

	@unittest.skip("does not detect an incorrect username")
	def test_Server401PlistFormatIncorrectUsernamePostSkipped(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print 'E'

	def test_Server403PlistFormatIncorrectUsernamePostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode )
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print '27'

	@unittest.expectedFailure
	def test_Server500PlistFormatEmptyUsernamePostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.emptyUser, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print '28'

	@unittest.skip('cannot detect the lack of a username')
	def test_Server401PlistFormatNoUsernamePostSkipped(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print 'F'

	def test_Server403PlistFormatNoUsernamePostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print '29'

	def test_Server401PlistFormatIncorrectPasswordPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print '30'

	def test_Server401PlistFormatEmptyPasswordPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print '31'

	def test_Server401PlistFormatNoPasswordPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, password=ServerTests.emptyPassword, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print '32'

	def test_Server403PlistFormatOtherPersonsPathPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, ServerTests.postPut_info, username=ServerTests.otherUser, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print '33'

	def test_Server201PlistFormatNonExsistantTypePostTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.NoTypeNoID)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.NoTypeNoID)
		tester.postTest(ServerTests.NoTypeNoID, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoTypeNoID, ID=bodyDataExtracter.id)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.NoTypeNoID)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID)
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Group time should have changed')
		self.assertRaises(KeyError, ServerTests.test.postException, oldGroup, bodyDataExtracter.id)
		#print '34'

	def test_Server201PlistFormatNonExsistantGroupPostTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.NoGroupNoID)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.NoGroupNoID)
		tester.postTest(ServerTests.NoGroupNoID, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter,
														  format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoGroupNoID, ID=bodyDataExtracter.id)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.NoGroupNoID)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID)
		self.assertEqual(oldGroupTime, ServerTests.NotFound)
		self.assertRaises(TypeError, ServerTests.test.postException, oldGroup, bodyDataExtracter.id)
		#print '35'

	def test_Server500PlistFormatWrongDatatypePostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTime)
		tester.postTest(ServerTests.URL_post, dict=ServerTests.WrongType, bodyDataExtracter=bodyDataExtracter)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		#print '36'

	#-----------------------------------
#		*************
#		* Put Tests *
#		*************

	#-----------------------------------

	def test_Server200DefaultPutTestCase(self):
		bodyDataExtracter = URL_Successful_Put_Response()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)

		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)

		tester.putTest(ServerTests.URL_json, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '37'

	def test_Server200JsonFormatPutTestCase(self):
		bodyDataExtracter = URL_Successful_Put_Response()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)

		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)

		tester.putTest(ServerTests.URL_json, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter,
														 format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '38'

	@unittest.skip("does not detect an incorrect username")
	def test_Server401JsonFormatIncorrectUsernamePutSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print 'G'

	def test_Server403JsonFormatIncorrectUsernamePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '39'

	@unittest.expectedFailure
	def test_Server500JsonFormatEmptyUsernamePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								username=ServerTests.emptyUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '40'

	@unittest.skip("does not detect an incorrect username")
	def test_Server401JsonFormatNoUsernamePutSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print 'H'

	def test_Server403JsonFormatNoUsernamePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '41'

	def test_Server401JsonFormatIncorrectPasswordPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '42'

	def test_Server401JsonFormatEmptyPasswordPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								password=ServerTests.emptyPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '43'

	def test_Server401JsonFormatNoPasswordPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								password=ServerTests.noPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '44'

	def test_Server403JsonFormatOtherPersonsPathPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, dict=ServerTests.postPut_info,
								username=ServerTests.otherUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '45'

	def test_Server201JsonFormatNonExsistantTypePutTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.NoTypeGroup)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.NoTypeGroup)
		tester.putTest(ServerTests.NoTypeWithID, ServerTests.postPut_info,
					bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoTypeWithID)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.NoTypeGroup)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'body expected to change')
		#print '46'

	def test_Server201JsonFormatNonExsistantGroupPutTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.NoGroupGroup)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.NoGroupGroup)
		tester.putTest(ServerTests.NoGroupWithID, ServerTests.postPut_info,
					bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoGroupWithID)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.NoGroupGroup)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp)
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'body expected to change')
		#print '47'

	def test_Server201JsonFormatNonExsistantIDPutTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.NoID, ServerTests.postPut_info,
					bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoID)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'body expected to change')
		#print '48'

	def test_Server500JsonFormatWrongDatatypePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_json)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_json, ServerTests.WrongType, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_json)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '49'

	#-----------------------------------

	def test_Server200PlistFormatPutTestCase(self):
		bodyDataExtracter = URL_Successful_Put_Response()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, ServerTests.postPut_info, bodyDataExtracter=bodyDataExtracter,
														 format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.OK, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		self.assertNotEqual(ServerTests.plist_oldGroup.getBody(oldGroup), bodyDataExtracter.body, 'body expected to change')
		#print '50'

	@unittest.skip("does not detect an incorrect username")
	def test_Server401PlistFormatIncorrectUsernamePutSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print 'I'

	def test_Server403PlistFormatIncorrectUsernamePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '51'

	@unittest.expectedFailure
	def test_Server500PlistFormatEmptyUsernamePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		ServerTests.tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								username=ServerTests.emptyUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '52'

	@unittest.skip("does not detect an incorrect username")
	def test_Server401PlistFormatNoUsernamePutSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print 'J'

	def test_Server403PlistFormatNoUsernamePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode )
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '53'

	def test_Server401PlistFormatIncorrectPasswordPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '54'

	def test_Server401PlistFormatEmptyPasswordPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								password=ServerTests.emptyPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '55'

	def test_Server401PlistFormatNoPasswordPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								password=ServerTests.noPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '56'

	def test_Server403PlistFormatOtherPersonsPathPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, dict=ServerTests.postPut_info,
								username=ServerTests.otherUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '57'

	def test_Server201PlistFormatNonExsistantTypePutTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.NoTypeGroup)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.NoTypeGroup)
		tester.putTest(ServerTests.NoTypeWithID, ServerTests.postPut_info,
					bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoTypeWithID)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.NoTypeGroup)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'body expected to change')
		#print '58'

	def test_Server201PlistFormatNonExsistantGroupPutTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.NoGroupGroup)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.NoGroupGroup)
		tester.putTest(ServerTests.NoGroupWithID, ServerTests.postPut_info,
					bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoGroupWithID)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.NoGroupGroup)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'body expected to change')
		#print '59'

	def test_Server201PlistFormatNonExsistantIDPutTestCase(self):
		bodyDataExtracter = URL_Create()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		oldGroup		 = ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.NoID, ServerTests.postPut_info,
					bodyDataExtracter=bodyDataExtracter, format=ServerTests.plist)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.NoID)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.SuccessfulAdd, body=ServerTests.postPut_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'body expected to change')
		#print '60'

	def test_Server500PlistFormatWrongDatatypePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		ServerTests.tester.getBody(ServerTests.URL_post)
		oldGroupTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.putTest(ServerTests.URL_plist, ServerTests.WrongType, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = ServerTests.tester.getLastModified(ServerTests.URL_plist)
		modifiedTimeGrp  = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		#print '61'

	#-----------------------------------
#		****************
#		* Delete Tests *
#		****************

	#-----------------------------------

	def test_Server204DefaultDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.SuccessfulDelete, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to delete to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertGreaterEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '62'

	def test_Server404GroupDeleteTestCase(self):
		bodyDataExtracter = URL_Group()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.NotAllowed, body=ServerTests.default_return)
		tester.deleteTest(ServerTests.URL_post, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')

	def test_Server204JsonFormatDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.SuccessfulDelete, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to delete to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertGreaterEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '63'

	@unittest.skip("cannot detect an incorrect Username")

	def test_Server401JsonFormatIncorrectUsernameDeleteTestCaseSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print 'K'

	def test_Server403JsonFormatIncorrectUsernameDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '64'

	@unittest.expectedFailure
	def test_Server500JsonFormatEmptyUsernameDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.emptyUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '65

	@unittest.skip("cannot detect the lack of a username")
	def test_Server401JsonFormatNoUsernameDeleteTestCaseSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print 'L'

	def test_Server403JsonFormatNoUsernameDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '66'

	def test_Server401JsonFormatIncorrectPasswordDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '67'

	def test_Server401JsonFormatEmptyPasswordDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, password=ServerTests.emptyPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '68'

	def test_Server401JsonFormatNoPasswordDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, password=ServerTests.noPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '69'

	def test_Server403JsonFormatOtherPersonsPathDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.otherUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '70'

	def test_Server404JsonFormatNonExsistantGroupDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.NoGroupWithID, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.NotFound, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Group modification time unexpectedly changed')
		#print '72'

	def test_Server404JsonFormatNonExsistantIDDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.NoID, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.NotFound, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Group modification time unexpectedly changed')
		#print '73'

	@unittest.expectedFailure
	def test_ServerDeleteGroupSameNameDifType(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		#expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		body1 = tester.getBody(ServerTests.TypeGroupIDURL)
		tester.deleteTest(ServerTests.JunkGroupIDURL, bodyDataExtracter=bodyDataExtracter)
		body2 = tester.getBody(ServerTests.TypeGroupIDURL)
		self.assertEqual(body1, body2, 'deleting a group/ID with the same name as another group/ID in a different Type has shard effects')
		#print '73'

	#-----------------------------------

	def test_Server204PlistFormatDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.SuccessfulDelete, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to delete to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertGreaterEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '74'

	@unittest.skip("cannot detect an incorrect Username")
	def test_Server401PlistFormatIncorrectUsernameDeleteTestCaseSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print 'M'

	def test_Server403PlistFormatIncorrectUsernameDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.incorrectUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode)
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '75'

	@unittest.expectedFailure
	def test_Server500PlistFormatEmptyUsernameDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.emptyUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.WrongType, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '76'

	@unittest.skip("cannot detect the lack of a username")
	def test_Server401PlistFormatNoUsernameDeleteTestCaseSkipped(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json,username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print 'N'

	def test_Server403PlistFormatNoUsernameDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.noUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '77'

	def test_Server401PlistFormatIncorrectPasswordDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, password=ServerTests.incorrectPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '78'

	def test_Server401PlistFormatEmptyPasswordDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, password=ServerTests.emptyPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '79'

	def test_Server401PlistFormatNoPasswordDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, password=ServerTests.noPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Unauthorized, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to delete to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '80'

	def test_Server403PlistFormatOtherPersonsPathDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.URL_json, username=ServerTests.otherUser, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		ServerTests.tester.getBody(ServerTests.URL_json, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.Forbidden, body=ServerTests.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '81'

	def test_Server404PlistFormatNonExsistantGroupDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.NoGroupWithID, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.NotFound, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '83'

	def test_Server404PlistFormatNonExsistantIDDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.setDefaults(tester)
		modifiedTimeOld	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		tester.deleteTest(ServerTests.NoID, bodyDataExtracter=bodyDataExtracter, format=ServerTests.json)
		modifiedTime	 = ServerTests.tester.getLastModified(ServerTests.URL_post)
		expectedValues.setValues(code=ServerTests.NotFound, body=ServerTests.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		#print '84'

def testAll():
	return testGetTest() + testPostTest() + testPutTest() + testDeleteTest()

def testGetTest():
	return testStandardGetTest() + testUnAthorizedGetTest() +testOtherPersonGetTest() + testNonExsistGetTest()

def testDefaultGetTest():
	return ['test_Server200DefaultGetTestCase']

def testStandardGetTest():
	return ['test_Server200DefaultGetTestCase', 'test_Server200GroupGetTestCase', 'test_Server200TypeGetTestCase',
		'test_Server200JsonFormatGetTestCase', 'test_Server200PlistFormatGetTestCase']

def testUnAthorizedGetTest():
	return ['test_Server200IncorrectUsernameGetTestCase', 'test_Server401EmptyUsernameGetTestCase', 'test_Server200NoUsernameGetTestCase',
			'test_Server401IncorrectPasswordGetTestCase', 'test_Server401EmptyPasswordGetTestCase', 'test_Server401NoPasswordGetTestCase']

def testOtherPersonGetTest():
	return ['test_Server200OtherPersonsPathGetTestCase']

def testNonExsistGetTest():
	return ['test_Server404NonExsistantTypeGetTestCase', 'test_Server404NonExsistantGroupGetTestCase', 'test_Server404NonExsistantIDGetTestCase']

def testPostTest():
	return testJsonPostTest() + testPlistPostTest()

def testJsonPostTest():
	return testJsonStandardPostTest() + testJsonUnAuthorizedPostTest() + testJsonOtherPersonPostTest() + testJsonNonExsistPostTest() + \
			testJsonWrongDataTypePostTest()

def testPlistPostTest():
	return testPlistStandardPostTest() + testPlistUnAuthorizedPostTest() + testPlistOtherPersonPostTest() + testPlistNonExsistPostTest() + \
			testPlistWrongDataTypePostTest()

def testDefaultPostTest():
	return ['test_Server201DefaultPostTestCase']

def testJsonStandardPostTest():
	return ['test_Server201DefaultPostTestCase', 'test_Server201JsonFormatPostTestCase']

def testJsonUnAuthorizedPostTest():
	return ['test_Server403JsonFormatIncorrectUsernamePostTestCase', 'test_Server500JsonFormatEmptyUsernamePostTestCase',
			'test_Server403JsonFormatNoUsernamePostTestCase', 'test_Server401JsonFormatIncorrectPasswordPostTestCase',
			'test_Server401JsonFormatEmptyPasswordPostTestCase', 'test_Server401JsonFormatNoPasswordPostTestCase', ]

def testJsonOtherPersonPostTest():
	return ['test_Server403JsonFormatOtherPersonsPathPostTestCase']

def testJsonNonExsistPostTest():
	return ['test_Server201JsonFormatNonExsistantTypePostTestCase', 'test_Server201JsonFormatNonExsistantGroupPostTestCase']

def testJsonWrongDataTypePostTest():
	return ['test_Server500JsonFormatWrongDatatypePostTestCase']

def testPlistStandardPostTest():
	return ['test_Server201DefaultPostTestCase', 'test_Server201PlistFormatPostTestCase']

def testPlistUnAuthorizedPostTest():
	return ['test_Server403PlistFormatIncorrectUsernamePostTestCase', 'test_Server500PlistFormatEmptyUsernamePostTestCase',
			'test_Server403PlistFormatNoUsernamePostTestCase', 'test_Server401PlistFormatIncorrectPasswordPostTestCase',
			'test_Server401PlistFormatEmptyPasswordPostTestCase', 'test_Server401PlistFormatNoPasswordPostTestCase', ]

def testPlistOtherPersonPostTest():
	return ['test_Server403PlistFormatOtherPersonsPathPostTestCase']

def testPlistNonExsistPostTest():
	return ['test_Server201PlistFormatNonExsistantTypePostTestCase', 'test_Server201PlistFormatNonExsistantGroupPostTestCase']

def testPlistWrongDataTypePostTest():
	return ['test_Server500PlistFormatWrongDatatypePostTestCase']

def testPutTest():
	return testJsonPutTest() + testPlistPutTest()

def testJsonPutTest():
	return testJsonStandardPutTest() + testJsonUnAuthorizedPutTest() + testJsonOtherPersonPutTest() + testJsonNonExsistPutTest() + \
			testJsonWrongDataTypePutTest()

def testPlistPutTest():
	return testPlistStandardPutTest() + testPlistUnAuthorizedPutTest() + testPlistOtherPersonPutTest() + testPlistNonExsistPutTest() + \
			testPlistWrongDataTypePutTest()

def testDefaultPutTest():
	return ['test_Server200DefaultPutTestCase']

def testJsonStandardPutTest():
	return ['test_Server200DefaultPutTestCase', 'test_Server200JsonFormatPutTestCase']

def testJsonUnAuthorizedPutTest():
	return ['test_Server403JsonFormatIncorrectUsernamePutTestCase', 'test_Server500JsonFormatEmptyUsernamePutTestCase',
			'test_Server403JsonFormatNoUsernamePutTestCase', 'test_Server401JsonFormatIncorrectPasswordPutTestCase',
			'test_Server401JsonFormatEmptyPasswordPutTestCase', 'test_Server401JsonFormatNoPasswordPutTestCase', ]

def testJsonOtherPersonPutTest():
	return ['test_Server403JsonFormatOtherPersonsPathPutTestCase']

def testJsonNonExsistPutTest():
	return ['test_Server201JsonFormatNonExsistantTypePutTestCase', 'test_Server201JsonFormatNonExsistantGroupPutTestCase',
			'test_Server201JsonFormatNonExsistantIDPutTestCase']

def testJsonWrongDataTypePutTest():
	return ['test_Server500JsonFormatWrongDatatypePutTestCase']

def testPlistStandardPutTest():
	return ['test_Server200DefaultPutTestCase', 'test_Server200PlistFormatPutTestCase']

def testPlistUnAuthorizedPutTest():
	return ['test_Server403PlistFormatIncorrectUsernamePutTestCase', 'test_Server500PlistFormatEmptyUsernamePutTestCase',
			'test_Server403PlistFormatNoUsernamePutTestCase', 'test_Server401PlistFormatIncorrectPasswordPutTestCase',
			'test_Server401PlistFormatEmptyPasswordPutTestCase', 'test_Server401PlistFormatNoPasswordPutTestCase', ]

def testPlistOtherPersonPutTest():
	return ['test_Server403PlistFormatOtherPersonsPathPutTestCase']

def testPlistNonExsistPutTest():
	return ['test_Server201PlistFormatNonExsistantTypePutTestCase', 'test_Server201PlistFormatNonExsistantGroupPutTestCase',
			'test_Server201PlistFormatNonExsistantIDPutTestCase']

def testPlistWrongDataTypePutTest():
	return ['test_Server500PlistFormatWrongDatatypePutTestCase']

def testDeleteTest():
	return testJsonDeleteTest() + testPlistDeleteTest()

def testJsonDeleteTest():
	return testJsonStandardDeleteTest() + testJsonUnAuthorizedDeleteTest() + testJsonOtherPersonDeleteTest() + testJsonNonExsistDeleteTest()

def testPlistDeleteTest():
	return testPlistStandardDeleteTest() + testPlistUnAuthorizedDeleteTest() + testPlistOtherPersonDeleteTest() + testPlistNonExsistDeleteTest()

def testDefaultDeleteTest():
	return ['test_Server204DefaultDeleteTestCase']

def testJsonStandardDeleteTest():
	return ['test_Server204DefaultDeleteTestCase', 'test_Server404GroupDeleteTestCase', 'test_Server204JsonFormatDeleteTestCase']

def testJsonUnAuthorizedDeleteTest():
	return ['test_Server403JsonFormatIncorrectUsernameDeleteTestCase', 'test_Server500JsonFormatEmptyUsernameDeleteTestCase',
			'test_Server403JsonFormatNoUsernameDeleteTestCase', 'test_Server401JsonFormatIncorrectPasswordDeleteTestCase',
			'test_Server401JsonFormatEmptyPasswordDeleteTestCase', 'test_Server401JsonFormatNoPasswordDeleteTestCase']

def testJsonOtherPersonDeleteTest():
	return ['test_Server403JsonFormatOtherPersonsPathDeleteTestCase']

def testJsonNonExsistDeleteTest():
	return ['test_Server404JsonFormatNonExsistantGroupDeleteTestCase', 'test_Server404JsonFormatNonExsistantIDDeleteTestCase', 'test_ServerDeleteGroupSameNameDifType']

def testPlistStandardDeleteTest():
	return ['test_Server204DefaultDeleteTestCase', 'test_Server204PlistFormatDeleteTestCase']

def testPlistUnAuthorizedDeleteTest():
	return ['test_Server403PlistFormatIncorrectUsernameDeleteTestCase', 'test_Server500PlistFormatEmptyUsernameDeleteTestCase',
			'test_Server403PlistFormatNoUsernameDeleteTestCase', 'test_Server401PlistFormatIncorrectPasswordDeleteTestCase',
			'test_Server401PlistFormatEmptyPasswordDeleteTestCase', 'test_Server401PlistFormatNoPasswordDeleteTestCase']

def testPlistOtherPersonDeleteTest():
	return ['test_Server403PlistFormatOtherPersonsPathDeleteTestCase']

def testPlistNonExsistDeleteTest():
	return ['test_Server404PlistFormatNonExsistantGroupDeleteTestCase', 'test_Server404PlistFormatNonExsistantIDDeleteTestCase']

if __name__ == '__main__':
	which_shell_to_run = testAll()
	unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(map(ServerTests, which_shell_to_run)))
