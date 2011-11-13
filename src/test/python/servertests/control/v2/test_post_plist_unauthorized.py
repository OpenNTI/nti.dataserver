from url_functionality import URL_oldGroup_json
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class PlistUnAuthorizedPostTest(V2TestCase):
	
	def _run_test(self, code, username):
		tester = self.controller()
		expectedValues = URLFunctionality()
		bde = URL_oldGroup_json()
				
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=code, body=self.default_return, lastModified=modifiedTime)
		tester.postTest(self.URL_post, self.postPut_info, username=username, bodyDataExtracter=bde)
		
		self.assertEqual(bde.responseCode, expectedValues.responseCode, "supposed to not allow access to wrong user / bad access info")
		self.assertEqual(bde.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bde.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		
	def test_Server403PlistFormatIncorrectUsernamePostTestCase(self):
		self._run_test(code=self.Forbidden, username=self.incorrectUser)

	def test_Server403PlistFormatNoUsernamePostTestCase(self):
		self._run_test(code=self.Forbidden, username=self.noUser)
		
	def test_Server500PlistFormatEmptyUsernamePostTestCase(self):
		self._run_test(code=self.WrongType, username=self.emptyUser)

	# -----------------------------

	def _run_401_test(self, password):
		tester = self.controller()
		expectedValues = URLFunctionality()
		bodyDataExtracter = URL_oldGroup_json()
				
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.Unauthorized, body=self.default_return, lastModified=modifiedTime)
		tester.postTest(self.URL_post, self.postPut_info, password=password, bodyDataExtracter=bodyDataExtracter)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		
	def test_Server401PlistFormatIncorrectPasswordPostTestCase(self):
		self._run_401_test(password=self.incorrectPassword)
	
	def test_Server401PlistFormatEmptyPasswordPostTestCase(self):
		self._run_401_test(password=self.emptyPassword)
	
	def test_Server401PlistFormatNoPasswordPostTestCase(self):
		self._run_401_test(password=self.noPassword)
		
if __name__ == '__main__':
	import unittest
	unittest.main()
