from url_functionality import URL_Create
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control.v2 import V2TestCase

class JsonStandardPostTest(V2TestCase):
	
	def _run_test(self, fmt=NoFormat()):
		tester = self.controller()
		bodyDataExtracter = URL_Create()
		expectedValues = URLFunctionality()
		
		if fmt != self.json:
			oldGroup = tester.getBody(self.URL_post)
			oldGroupTime = tester.getLastModified(self.URL_post)
			
		tester.postTest(self.URL_post, self.postPut_info, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID  = tester.getLastModified(self.URL_post, ID=bodyDataExtracter.id)
		modifiedTimeGrp = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.SuccessfulAdd, body=self.postPut_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		
		if fmt != self.json:
			self.assertLess(oldGroupTime, modifiedTimeGrp, 'oldGroupTime unexpectedly greater than modifiedTimeGrp')
			self.assertRaises(KeyError, self.test.postException, oldGroup, bodyDataExtracter.id)
			
	def test_Server201DefaultPostTestCase(self):
		self._run_test()

	def test_Server201JsonFormatPostTestCase(self):
		self._run_test(fmt=self.json)
		
if __name__ == '__main__':
	import unittest
	unittest.main()
