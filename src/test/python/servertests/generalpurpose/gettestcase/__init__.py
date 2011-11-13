'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose.utilities import RunTest
from servertests.generalpurpose.utilities.server_call_type import GetTest
from servertests.generalpurpose.utilities.body_data_extracter import URLFunctionality
from servertests.generalpurpose.utilities.url_formatter import NoFormat

class GetTests(RunTest):
	
	VOID_VALUE = 'not set'
	
	def __init__(self, clazz, constants_object, *args, **kwargs):
		self.expectedValues = URLFunctionality()
		self.constants_object = constants_object
		super(GetTests, self).__init__(clazz, constants_object, self.expectedValues, *args, **kwargs)
	
	def okGetTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=NoFormat()):
		self.expectedValues.setValues(code=self.constants_object.OK, body=self.constants_object.DEFAULT_RETURN, 
			ifModifiedSinceError=self.constants_object.NotModifiedSince, ifModifiedSinceSuccess=self.constants_object.OK)
		self.runTestType(GetTest(), self.object.getTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.bodyDataExtracter.ifModifiedSinceError, self.expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(self.bodyDataExtracter.ifModifiedSinceSuccess, self.expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is modifying the lastModified time')
		
	def unauthorizedGetTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=NoFormat()):
		self.expectedValues.setValues(code=self.constants_object.Unauthorized, body=self.constants_object.DEFAULT_RETURN, 
			ifModifiedSinceError=self.constants_object.NotModifiedSince, ifModifiedSinceSuccess=self.constants_object.OK)
		self.runTestType(GetTest(), self.object.getTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is modifying the lastModified time')
		
	def notFoundGetTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=NoFormat()):
		self.expectedValues.setValues(code=self.constants_object.NotFound, body=self.constants.NotFound, 
			ifModifiedSinceError=self.constants_object.NotModifiedSince, ifModifiedSinceSuccess=self.constants_object.OK)
		self.runTestType(GetTest(), self.object.getTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is modifying the lastModified time')