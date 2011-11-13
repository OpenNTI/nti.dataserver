'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose.utilities import RunTest
from servertests.generalpurpose.utilities.server_call_type import PutTest
from servertests.generalpurpose.utilities.body_data_extracter import URLFunctionality
from servertests.generalpurpose.utilities.url_formatter import NoFormat
from servertests.generalpurpose.utilities.url_formatter import JsonFormat
from servertests.generalpurpose.utilities.url_formatter import PlistFormat

class PutTests(RunTest):
	
	VOID_VALUE = 'not set'
	
	def __init__(self, clazz, constants_object, *args, **kwargs):
		self.expectedValues = URLFunctionality()
		self.constants_object = constants_object
		super(PutTests, self).__init__(clazz, constants_object, self.expectedValues, *args, **kwargs)
	
	def okPutTest(self, url=VOID_VALUE, urlGroup=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=NoFormat(), data=VOID_VALUE):
		self.expectedValues.setValues(code=self.constants_object.OK, body=self.constants_object.POST_PUT_RETURN)
		self.runTestType(PutTest(), self.object.putTest, newURL=url, newURLGroup=urlGroup, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt, data=data)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertGreater(self.lastModifiedTime, self.lastModifiedTimeOld, 'Wrong ID modification time')
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'Wrong group modification time')
		self.assertLess(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'Wrong group modification time')
		
	def notAllowedPutTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, fmt=NoFormat()):
		self.expectedValues.setValues(code=self.constants_object.NotAllowed, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(PutTest(), self.object.putTest, newURL=url, username=username, password=password, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is unexpectedly modifying the lastModified time')
		
	def successfulAddPutTestJsonFormat(self, url=VOID_VALUE, urlGroup=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=JsonFormat()):
		self.expectedValues.setValues(code=self.constants_object.SuccessfulAdd, body=self.constants_object.POST_PUT_RETURN)
		self.runTestType(PutTest(), self.object.putTest, newURL=url, newURLGroup=urlGroup, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertGreater(self.lastModifiedTime, self.lastModifiedTimeOld, 'Wrong ID modification time')
#		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'Wrong group modification time')
		self.assertLess(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'Wrong group modification time')
		
	def successfulAddPutTestPlistFormat(self, url=VOID_VALUE, urlGroup=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=PlistFormat()):
		self.expectedValues.setValues(code=self.constants_object.SuccessfulAdd, body=self.constants_object.POST_PUT_RETURN)
		self.runTestType(PutTest(), self.object.putTest, newURL=url, newURLGroup=urlGroup, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertGreater(self.lastModifiedTime, self.lastModifiedTimeOld, 'Wrong ID modification time')
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'Wrong group modification time')
		self.assertLess(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'Wrong group modification time')
		
	def unauthorizedPutTestJsonFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=JsonFormat(), overRide=False):
		self.expectedValues.setValues(code=self.constants_object.Unauthorized, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(PutTest(), self.object.putTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter, overRide=overRide)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'Wrong ID modification time')
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'Wrong group modification time')
		self.assertEqual(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'Wrong group modification time')
		
	def unauthorizedPutTestPlistFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=PlistFormat(), overRide=False):
		self.expectedValues.setValues(code=self.constants_object.Unauthorized, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(PutTest(), self.object.putTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter, overRide=overRide)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'Wrong ID modification time')
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'Wrong group modification time')
		self.assertEqual(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'Wrong group modification time')
		
	def wrongTypePutTestJsonFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=JsonFormat(), data=VOID_VALUE):
		self.expectedValues.setValues(code=self.constants_object.WrongType, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(PutTest(), self.object.putTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt, data=data)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'Wrong ID modification time')
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'Wrong group modification time')
		self.assertEqual(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'Wrong group modification time')
		
	def wrongTypePutTestPlistFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=PlistFormat(), data=VOID_VALUE):
		self.expectedValues.setValues(code=self.constants_object.WrongType, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(PutTest(), self.object.putTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt, data=data)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'Wrong ID modification time')
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'Wrong group modification time')
		self.assertEqual(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'Wrong group modification time')
		
		