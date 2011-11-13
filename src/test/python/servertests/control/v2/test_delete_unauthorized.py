from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase
from servertests.control import VOID_VALUE

class JsonUnAuthorizedDeleteTest(V2TestCase):

	def _run_test(self, code, username=VOID_VALUE, password=VOID_VALUE):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		modifiedTimeOld	= tester.getLastModified(self.URL_post)
		tester.deleteTest(self.URL_json, username=username, password=password, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(self.URL_post)
		
		expectedValues.setValues(code=code, body=self.default_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')
		
	def test_Server403JsonFormatIncorrectUsernameDeleteTestCase(self):
		self._run_test(code=self.Forbidden, username=self.incorrectUser)

	def test_Server500JsonFormatEmptyUsernameDeleteTestCase(self):
		self._run_test(code=self.WrongType, username=self.emptyUser)

	def test_Server403JsonFormatNoUsernameDeleteTestCase(self):
		self._run_test(code=self.Forbidden, username=self.noUser)

	def test_Server401JsonFormatIncorrectPasswordDeleteTestCase(self):
		self._run_test(code=self.Unauthorized, password=self.incorrectPassword)

	def test_Server401JsonFormatEmptyPasswordDeleteTestCase(self):
		self._run_test(code=self.Unauthorized, password=self.emptyPassword)

	def test_Server401JsonFormatNoPasswordDeleteTestCase(self):
		self._run_test(code=self.Unauthorized, password=self.noPassword)

if __name__ == '__main__':
	import unittest
	unittest.main()
