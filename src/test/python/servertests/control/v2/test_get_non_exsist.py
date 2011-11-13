from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class NonExsistGetTest(V2TestCase):
	
	def _run_test(self,  url):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		tester.getTest(url, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(url)
		expectedValues.setValues(code=self.NotFound, body=self.NotFound, lastModified=modifiedTime)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found to read from')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		
	def test_Server404NonExsistantTypeGetTestCase(self):
		self._run_test(self.NonExsistTypeURL)
		
	def test_Server404NonExsistantGroupGetTestCase(self):
		self._run_test(self.NonExsistGroupURL)
		
	def test_Server404NonExsistantIDGetTestCase(self):
		self._run_test(self.NonExsistID_URL)
	
if __name__ == '__main__':
	import unittest
	unittest.main()
