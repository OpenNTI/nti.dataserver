'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests import DataServerTestCase

class ServerStart(DataServerTestCase):
	
	def __init__(self, clazz, constants, expectedValues, *args, **kwargs):
		super(ServerStart, self ).__init__(*args, **kwargs)
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
		self.object = self.clazz()
		self.object.setUp(self.constants)
		
	def tearDown(self):
		self.object =  None

	def assertResponsePartsEqual(self, bodyDataExtracter):
		self.assertEqual(bodyDataExtracter.responseCode, self.expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, self.expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, self.expectedValues.lastModified, 'Wrong ID modification time')
