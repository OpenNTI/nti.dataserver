'''
Created on Oct 3, 2011

@author: ltesti
'''
from servertests.generalpurpose.utilities.url_formatter import NoFormat
from servertests import DataServerTestCase

class UnitTestController(DataServerTestCase):
	
	def __init__(self, clazz, constants, expectedValues, *args, **kwargs):
		super(UnitTestController, self ).__init__(*args, **kwargs)
		self.clazz = clazz
		self.object = None
		self.constants = constants
		self.expectedValues = expectedValues
		
	@classmethod
	def setUpClass(cls):
		DataServerTestCase.setUpClass()
	
	@classmethod
	def tearDownClass(cls):	
		DataServerTestCase.tearDownClass()
		
	def setUp(self):
		self.newID = None
		self.object = self.clazz()
		self.incrementingIDs = self.object.setUp(self.constants)
		
	def tearDown(self):
		if self.object:
			self.object.tearDown(self.constants)
		self.object =  None

	def assertResponsePartsEqual(self, bodyDataExtracter, overRide=False):
		if overRide == False:
			self.assertEqual(bodyDataExtracter.responseCode, self.expectedValues.responseCode, "Didn't open URL and read URL")
		else: 
			if bodyDataExtracter.responseCode != self.constants.Unauthorized and bodyDataExtracter.responseCode != self.constants.Forbidden:
				self.fail('This test expected the response to be unauthorized or forbidden')
		self.assertEqual(bodyDataExtracter.body, self.expectedValues.body, 'Incorrect Body')

class RunTest(UnitTestController):
	
	VOID_VALUE = 'not set'
	
	def __init__(self, clazz, constants, expectedValues, *args, **kwargs):
		super(RunTest, self).__init__(clazz, constants, expectedValues, *args, **kwargs)
	
	def runTestType(self, type_object, type_constants, newURL=VOID_VALUE, newURLGroup=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=NoFormat(), data=VOID_VALUE):
		url, urlGroup, info, constants, self.bodyDataExtracter =  type_constants(bodyDataExtracter)
		if newURL != self.VOID_VALUE:
			url = newURL
		if newURLGroup != self.VOID_VALUE:
			urlGroup = newURLGroup
		if username == self.VOID_VALUE:
			username = constants.username
		if password == self.VOID_VALUE:
			password = constants.password
		if data != self.VOID_VALUE:
			info = data
		self.lastModifiedTimeOld = type_object.getLastModified(url, constants)
		self.lastModifiedTimeGroupOld = type_object.getLastModified(urlGroup, constants)
		postID = type_object.run(url, urlGroup, info, username=username, password=password, bodyDataExtracter=self.bodyDataExtracter, fmt=fmt)
		if postID:
			url = url + '/' + postID
		self.lastModifiedTimeGroup = type_object.getLastModified(urlGroup, constants)
		self.lastModifiedTime = type_object.getLastModified(url, constants)