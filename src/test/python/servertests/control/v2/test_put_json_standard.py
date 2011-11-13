from url_functionality import URL_Successful_Put_Response
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control.v2 import V2TestCase

class JsonStandardPutTest(V2TestCase):
	
	def _run_test(self, fmt=NoFormat()):
		tester = self.controller()
		expectedValues = URLFunctionality()
		bodyDataExtracter = URL_Successful_Put_Response()
						
		oldGroupTime = tester.getLastModified(self.URL_post)
		tester.putTest(self.URL_json, self.postPut_info, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		modifiedTimeID = tester.getLastModified(self.URL_json)
		modifiedTimeGrp = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.OK, body=self.postPut_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		
	def test_Server200DefaultPutTestCase(self):
		self._run_test()

	def test_Server200JsonFormatPutTestCase(self):
		self._run_test(fmt=self.json)
		
if __name__ == '__main__':
	import unittest
	unittest.main()
