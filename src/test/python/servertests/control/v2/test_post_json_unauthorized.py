from url_functionality import URL_oldGroup_json
from servertests.control import URLFunctionality
from servertests.control import VOID_VALUE
from servertests.control.v2 import V2TestCase

class JsonUnAuthorizedPostTest(V2TestCase):
	
	def _run_403_test(self, username=VOID_VALUE):
		tester = self.controller()
		expectedValues = URLFunctionality()
		bodyDataExtracter = URL_oldGroup_json()
				
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.Forbidden, body=self.default_return, lastModified=modifiedTime)
		tester.postTest(self.URL_post, self.postPut_info, username=username, bodyDataExtracter=bodyDataExtracter, fmt=self.json)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		
	def test_Server403JsonFormatIncorrectUsernamePostTestCase(self):
		self._run_403_test(username=self.incorrectUser)
		
	def test_Server403JsonFormatNoUsernamePostTestCase(self):
		self._run_403_test(username=self.noUser)
		
	# -----------------------------
		
	def test_Server500JsonFormatEmptyUsernamePostTestCase(self):
		tester = self.controller()
		expectedValues = URLFunctionality()
		bodyDataExtracter = URL_oldGroup_json()
		
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.WrongType, body=self.default_return, lastModified=modifiedTime)
		tester.postTest(self.URL_post, self.postPut_info, username=self.emptyUser, bodyDataExtracter=bodyDataExtracter, fmt=self.json)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		
	# -----------------------------
	
	def _run_401_test(self, password=VOID_VALUE):
		tester = self.controller()
		expectedValues = URLFunctionality()
		bodyDataExtracter = URL_oldGroup_json()
				
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.Unauthorized, body=self.default_return, lastModified=modifiedTime)
		tester.postTest(self.URL_post, self.postPut_info, password=password, bodyDataExtracter=bodyDataExtracter, fmt=self.json)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to post to URL')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		
	def test_Server401JsonFormatIncorrectPasswordPostTestCase(self):
		self._run_401_test(password=self.incorrectPassword)

	def test_Server401JsonFormatEmptyPasswordPostTestCase(self):
		self._run_401_test(password=self.emptyPassword)

	def test_Server401JsonFormatNoPasswordPostTestCase(self):
		self._run_401_test(password=self.noPassword)
		
if __name__ == '__main__':
	import unittest
	unittest.main()
