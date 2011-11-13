from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v3 import V3TestCase

class GetResponseVariableError(V3TestCase):

	def test_Server401IncorrectPasswordGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller_response()
		expectedValues    = URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(tester.addID(self.URL_resp_NoFormat, self.NoFormat_resp_ID), 
								password=self.incorrectPassword, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(tester.addID(self.URL_resp_NoFormat, self.NoFormat_resp_ID))
		expectedValues.setValues(code=self.Unauthorized, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		#print '31'

	def test_Server404NonExsistantIDGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller_response()
		expectedValues    = URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(self.URL_resp_NoID, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(self.URL_resp_NoID)
		expectedValues.setValues(code=self.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')

if __name__ == '__main__':
	import unittest
	unittest.main()
