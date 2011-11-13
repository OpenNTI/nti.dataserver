'''
Created on Oct 18, 2011

@author: ltesti
'''

from servertests.generalpurpose.utilities import RunTest
from servertests.generalpurpose.utilities.server_call_type import DeleteTest
from servertests.generalpurpose.utilities.body_data_extracter import URLFunctionality
from servertests.generalpurpose.utilities.url_formatter import NoFormat

class DeleteTests(RunTest):
	
	VOID_VALUE = 'not set'
	
	def __init__(self, clazz, constants_object, *args, **kwargs):
		self.expectedValues = URLFunctionality()
		self.constants_object = constants_object
		super(DeleteTests, self).__init__(clazz, constants_object, self.expectedValues, *args, **kwargs)
	
	def successfulDeleteTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		self.expectedValues.setValues(code=self.constants_object.SuccessfulDelete, body=self.constants_object.NotFound)
		self.runTestType(DeleteTest(), self.object.deleteTest, newURL=url, username=username, password=password, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertGreater(self.lastModifiedTimeGroup, self.lastModifiedTimeGroupOld, 'The Delete Test isnt modifying the lastModified time')
		
	def unauthorizedDeleteTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat(), overRide=False):
		self.expectedValues.setValues(code=self.constants_object.Unauthorized, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(DeleteTest(), self.object.deleteTest, newURL=url, username=username, password=password, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter, overRide=overRide)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Delete Test is unexpectedly modifying the lastModified time')
		self.assertEqual(self.lastModifiedTimeGroup, self.lastModifiedTimeGroupOld, 'The Delete Test is unexpectedly modifying the lastModified time')
		
	def notFoundDeleteTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		self.expectedValues.setValues(code=self.constants_object.NotFound, body=self.constants_object.NotFound)
		self.runTestType(DeleteTest(), self.object.deleteTest, newURL=url, username=username, password=password, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTimeGroup, self.lastModifiedTimeGroupOld, 'The Delete Test is unexpectedly modifying the lastModified time')
		
	def notAllowedDeleteTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat(), bodyDataExtracter=VOID_VALUE):
		self.expectedValues.setValues(code=self.constants_object.NotAllowed, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(DeleteTest(), self.object.deleteTest, newURL=url, username=username, password=password, fmt=fmt, bodyDataExtracter=bodyDataExtracter)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Delete Test is unexpectedly modifying the lastModified time')
		self.assertEqual(self.lastModifiedTimeGroup, self.lastModifiedTimeGroupOld, 'The Delete Test is unexpectedly modifying the lastModified time')
		
		