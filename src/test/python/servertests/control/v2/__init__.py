import time
import uuid

from servertests.control import NoFormat
from servertests.control import PostTest
from servertests.control import JsonFormat
from servertests.control import UserObject
from servertests.control import PlistFormat
from servertests.control import DefaultValues
from servertests.control import ServerController

from url_functionality import URL_oldGroup_json
from url_functionality import URL_oldGroup_plist

from servertests import DataServerTestCase

##########################
	
class V2Constants(object):
	
	def constants(self, url=None):
		self.URL				  = url or "http://localhost:8080"
		self.URL_DS				  = self.URL 	+ '/dataserver'
		self.URL_USERS			  = self.URL_DS + '/users'
		self.URL_TYPE             = self.URL_USERS + '/ltesti/TestType'
		self.URL_POST			  = self.URL_USERS + '/ltesti/TestType/TestGroup'
		self.URL_JSON			  = self.URL_USERS + '/ltesti/TestType/TestGroup/jsonID'
		self.URL_PLIST			  = self.URL_USERS + '/ltesti/TestType/TestGroup/plistID'
		self.URL_OTHER_POST	      = self.URL_USERS + '/sjohnson/TestType/TestGroup'
		self.URL_OTHER_PUT		  = self.URL_USERS + '/sjohnson/TestType/TestGroup/TestID'
		self.NON_EXSIST_TYPE_URL  = self.URL_USERS + '/ltesti/doesNotExist/TestGroup/TestID'
		self.NON_EXSIST_GROUP_URL = self.URL_USERS + '/ltesti/TestType/doesNotExist/TestID'
		self.NON_EXSIST_ID_URL	  = self.URL_USERS + '/ltesti/TestType/TestGroup/doesNotExist'
		self.DEFAULT_INFO		  = {"DefaultKey":"StartingInfo"}
		self.POST_PUT_INFO		  = {"PostPutKey":"NewInfo"}
		self.DEFAULT_RETURN_KEY   = 'DefaultKey'
		self.POST_PUT_RETURN_KEY  = 'PostPutKey'
		self.DEFAULT_RETURN	      = 'StartingInfo'
		self.POST_PUT_RETURN	  = 'NewInfo'
		self.INCORRECT_USER_PASS  = 'incorrect'
		self.EMPTY_USER_PASS	  = ''
		self.NO_USER_PASS		  = None
		
class V2TestCase(DataServerTestCase):
	
	@classmethod
	def setUpClass(cls):

		#******************************
		#*** Default inputs Section ***
		#******************************

		constants= V2Constants()
		constants.constants()
		
		cls.URL					= constants.URL
		cls.URL_DS				= constants.URL_DS
		cls.URL_USERS			= constants.URL_USERS
		cls.URL_type			= constants.URL_TYPE
		cls.URL_post		    = constants.URL_POST
		cls.URL_json		    = constants.URL_JSON
		cls.URL_plist		  	= constants.URL_PLIST
		cls.URL_other_post	  	= constants.URL_OTHER_POST
		cls.URL_other_put	  	= constants.URL_OTHER_PUT
		cls.NonExsistTypeURL	= constants.NON_EXSIST_TYPE_URL
		cls.NonExsistGroupURL	= constants.NON_EXSIST_GROUP_URL
		cls.NonExsistID_URL		= constants.NON_EXSIST_ID_URL
		cls.default_info		= constants.DEFAULT_INFO
		cls.postPut_info		= constants.POST_PUT_INFO
		cls.default_returnKey	= constants.DEFAULT_RETURN_KEY
		cls.postPut_returnKey	= constants.POST_PUT_RETURN_KEY
		cls.default_return		= constants.DEFAULT_RETURN
		cls.postPut_return		= constants.POST_PUT_RETURN
		cls.incorrectUser		= constants.INCORRECT_USER_PASS
		cls.incorrectPassword	= constants.INCORRECT_USER_PASS
		cls.emptyUser			= constants.EMPTY_USER_PASS
		cls.emptyPassword		= constants.EMPTY_USER_PASS
		cls.noUser				= constants.NO_USER_PASS
		cls.noPassword			= constants.NO_USER_PASS
		
		defaults				= DefaultValues()
		cls.path				= defaults.path
		cls.username			= defaults.username
		cls.otherUser			= defaults.otherUser
		cls.password			= defaults.password
		cls.incorrectPassword	= defaults.incorrectpassword
		cls.message				= defaults.message
		cls.void				= defaults.void
		cls.TinyNumber			= defaults.TinyNumber
		cls.LonelyNumber		= defaults.LonelyNumber
		cls.TheNumberTwo		= defaults.TheNumberTwo
		cls.TheNumberThree		= defaults.TheNumberThree
		cls.OK					= defaults.OK
		cls.SuccessfulAdd		= defaults.SuccessfulAdd
		cls.SuccessfulDelete	= defaults.SuccessfulDelete
		cls.NotModifiedSince	= defaults.NotModifiedSince
		cls.Unauthorized		= defaults.Unauthorized
		cls.Forbidden			= defaults.Forbidden
		cls.NotFound			= defaults.NotFound
		cls.NotAllowed			= defaults.NotAllowed
		cls.WrongType			= defaults.WrongType
		
		cls.ID_ltesti			= UserObject()
		cls.ID_sjohnson			= UserObject()
		cls.json				= JsonFormat()
		cls.plist				= PlistFormat()
		cls.noFormat			= NoFormat()
		cls.test				= PostTest()
		cls.json_oldGroup		= URL_oldGroup_json()
		cls.plist_oldGroup		= URL_oldGroup_plist()
		
		DataServerTestCase.setUpClass()
	
	@classmethod
	def tearDownClass(cls):	
		DataServerTestCase.tearDownClass()

	def setUp(self):
		super(V2TestCase, self).setUp()
		self.LIST_NAME='TestFriendsList-%s@nextthought.com' % time.time()
		
		# a set of puts and deletes that are set before each test
		tester = self.controller()
		tester.setUpPut(self.URL_json)
		tester.setUpPut(self.URL_plist, fmt=self.plist)
		tester.setUpPut(self.URL_other_put, username=self.otherUser, fmt=self.json)
		
		self.NoTypeGroup		= self.URL_USERS 	+ '/ltesti/' + str(uuid.uuid4()) + '/TestGroup'
		self.NoTypeWithID		= self.NoTypeGroup	+ '/TestID'
		self.NoGroupGroup		= self.URL_USERS	+ '/ltesti/TestType/' + str(uuid.uuid4())
		self.NoGroupWithID		= self.NoGroupGroup + '/TestID'
		self.NoID				= self.URL_USERS 	+ '/ltesti/TestType/TestGroup/' + str(uuid.uuid4())
		self.NoTypeNoID			= self.URL_USERS	+ '/ltesti/' + str(uuid.uuid4()) + '/TestGroup'
		self.NoGroupNoID		= self.URL_USERS	+ '/ltesti/TestType/' + str(uuid.uuid4())
		self.TypeGroupURL		= self.URL_USERS	+ '/ltesti/TestType1/TestGroup1/'
		self.SetUpPostID		= tester.setUpPost(self.TypeGroupURL, fmt=self.json)
		self.JunkGroupIDURL		= self.URL_USERS	+ '/ltesti/' + str(uuid.uuid4()) + '/TestGroup1/' + self.SetUpPostID
		self.TypeGroupIDURL		= self.URL_USERS	+ '/ltesti/TestType1/TestGroup1/' + self.SetUpPostID
											
	def tearDown(self):
		tester = self.controller()
		tester.tearDownDelete(self.URL_json)
		tester.tearDownDelete(self.URL_plist)
		tester.tearDownDelete(self.URL_other_put, username=self.otherUser)
		tester.tearDownDelete(tester.addID(self.URL_post, tester.newID))
		tester.tearDownDelete(self.NoTypeWithID)
		tester.tearDownDelete(self.NoGroupWithID)
		tester.tearDownDelete(self.NoID)
		tester.tearDownDelete(tester.addID(self.NoTypeNoID, tester.newID))
		tester.tearDownDelete(tester.addID(self.NoGroupNoID, tester.newID))
		
#	********************
#	*** Set Defaults ***
#	********************
		
	def controller(self):
		"""
		return a new server controller
		"""
		tester = ServerController()
		self.setDefaults(tester)
		return tester
	
	def setDefaults(self, obj):
		obj.create(self.username, self.password, self.default_info, self.ID_ltesti)
