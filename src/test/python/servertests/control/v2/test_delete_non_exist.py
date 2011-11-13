from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonNonExsistDeleteTest(V2TestCase):

	def _run_test(self, aid):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
		expectedValues  = URLFunctionality()
		
		modifiedTimeOld	 = tester.getLastModified(self.URL_post)
		tester.deleteTest(aid, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.NotFound, body=self.NotFound, lastModified=modifiedTime)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Group modification time unexpectedly changed')
		
	def test_Server404JsonFormatNonExsistantGroupDeleteTestCase(self):
		self._run_test(self.NoGroupWithID)
		
	def test_Server404JsonFormatNonExsistantIDDeleteTestCase(self):
		self._run_test(self.NoID)
		
	def test_ServerDeleteGroupSameNameDifType(self):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
	
		body1 = tester.getBody(self.TypeGroupIDURL)
		tester.deleteTest(self.JunkGroupIDURL, bodyDataExtracter=bodyDataExtracter)
		body2 = tester.getBody(self.TypeGroupIDURL)
		
		self.assertEqual(body1, body2, 
						'deleting a group/ID with the same name as another group/ID in a different Type has shard effects')

if __name__ == '__main__':
	import unittest
	unittest.main()
