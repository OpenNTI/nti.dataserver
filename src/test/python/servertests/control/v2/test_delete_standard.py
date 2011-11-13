from url_functionality import URL_Group
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonStandardDeleteTest(V2TestCase):

	def test_Server404GroupDeleteTestCase(self):
		tester = self.controller()	
		bodyDataExtracter = URL_Group()
		expectedValues = URLFunctionality()
		
		modifiedTimeOld = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.NotAllowed, body=self.default_return)
		tester.deleteTest(self.URL_post, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(self.URL_post)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')

if __name__ == '__main__':
	import unittest
	unittest.main()
