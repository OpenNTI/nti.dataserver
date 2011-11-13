'''
Created on Oct 4, 2011

@author: ltesti
'''
from servertests.generalpurpose.utilities import RunTest
from servertests.generalpurpose.utilities.server_call_type import PostTest
from servertests.generalpurpose.utilities.body_data_extracter import URLFunctionality
from servertests.generalpurpose.utilities.url_formatter import NoFormat
from servertests.generalpurpose.utilities.url_formatter import JsonFormat
from servertests.generalpurpose.utilities.url_formatter import PlistFormat
from servertests.generalpurpose.utilities.body_data_extracter import URL_Group
from servertests.generalpurpose.utilities.body_data_extracter import URL_DefaultV3_Quizzes

class PostTests(RunTest):
	
	VOID_VALUE = 'not set'
	
	def __init__(self, clazz, constants_object, *args, **kwargs):
		self.expectedValues = URLFunctionality()
		self.constants_object = constants_object
		super(PostTests, self).__init__(clazz, constants_object, self.expectedValues, *args, **kwargs)
	
	def successfulAddPostTest(self, url=VOID_VALUE, urlGroup=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=NoFormat(), data=VOID_VALUE, body=VOID_VALUE):
		if body == self.VOID_VALUE:
			body = self.constants_object.POST_PUT_RETURN
		self.expectedValues.setValues(code=self.constants_object.SuccessfulAdd, body=body)
		self.runTestType(PostTest(), self.object.postTest, newURL=url, newURLGroup=urlGroup, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt, data=data)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		self.assertLess(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'oldGroupTime unexpectedly greater than modifiedTimeGrp')
		
	def notAllowedPostTest(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=URL_DefaultV3_Quizzes(), fmt=NoFormat()):
		self.expectedValues.setValues(code=self.constants_object.NotAllowed, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(PostTest(), self.object.postTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is unexpectedly modifying the lastModified time')
		
	def successfulAddPostTestJsonFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=JsonFormat()):
		self.expectedValues.setValues(code=self.constants_object.SuccessfulAdd, body=self.constants_object.POST_PUT_RETURN)
		self.runTestType(PostTest(), self.object.postTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		self.assertLess(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'oldGroupTime unexpectedly greater than modifiedTimeGrp')
		
	def unauthorizedPostTestJsonFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=URL_Group(), fmt=JsonFormat(), overRide=False):
		self.expectedValues.setValues(code=self.constants_object.Unauthorized, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(PostTest(), self.object.postTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter, overRide=overRide)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is unexpectedly modifying the lastModified time')
		
	def improperInfoPostTestJsonFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=URL_Group(), fmt=JsonFormat(), info=VOID_VALUE):
		if info == self.VOID_VALUE:
			info = self.constants_object.POST_PUT_INFO
		self.expectedValues.setValues(code=self.constants_object.WrongType, body=self.constants.DEFAULT_RETURN)
		self.runTestType(PostTest(), self.object.postTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt, data=info)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is unexpectedly modifying the lastModified time')
		
	def successfulAddPostTestPlistFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=VOID_VALUE, fmt=PlistFormat()):
		self.expectedValues.setValues(code=self.constants_object.SuccessfulAdd, body=self.constants_object.POST_PUT_RETURN)
		self.runTestType(PostTest(), self.object.postTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertGreaterEqual(self.lastModifiedTimeGroup, self.lastModifiedTime, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		self.assertLess(self.lastModifiedTimeGroupOld, self.lastModifiedTimeGroup, 'oldGroupTime unexpectedly greater than modifiedTimeGrp')
		
	def unauthorizedPostTestPlistFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=URL_Group(), fmt=PlistFormat(), overRide=False):
		self.expectedValues.setValues(code=self.constants_object.Unauthorized, body=self.constants_object.DEFAULT_RETURN)
		self.runTestType(PostTest(), self.object.postTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter, overRide=overRide)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is unexpectedly modifying the lastModified time')
		
	def improperInfoPostTestPlistFormat(self, url=VOID_VALUE, username=VOID_VALUE, password=VOID_VALUE, bodyDataExtracter=URL_Group(), fmt=PlistFormat(), info=VOID_VALUE):
		if info == self.VOID_VALUE:
			info = self.constants_object.POST_PUT_INFO
		self.expectedValues.setValues(code=self.constants_object.WrongType, body=self.constants.DEFAULT_RETURN)
		self.runTestType(PostTest(), self.object.postTest, newURL=url, username=username, password=password, bodyDataExtracter=bodyDataExtracter, fmt=fmt, data=info)
		
		#runs the asserts
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.lastModifiedTime, self.lastModifiedTimeOld, 'The Get Test is unexpectedly modifying the lastModified time')