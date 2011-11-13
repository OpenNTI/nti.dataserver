from url_functionality import URL_oldGroup_json
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonOtherPersonPostTest(V2TestCase):
	
	def test_Server403JsonFormatOtherPersonsPathPostTestCase(self):
		bodyDataExtracter = URL_oldGroup_json()
		tester			  = self.controller()
		expectedValues    = URLFunctionality()
		
		modifiedTime	 = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.Forbidden, body=self.default_return, lastModified=modifiedTime)
		tester.postTest(self.URL_post, self.postPut_info, username=self.otherUser, bodyDataExtracter=bodyDataExtracter,
						fmt=self.json)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		
if __name__ == '__main__':
	import unittest
	unittest.main()
