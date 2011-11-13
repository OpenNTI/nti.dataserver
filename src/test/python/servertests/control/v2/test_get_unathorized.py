from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control import VOID_VALUE
from servertests.control.v2 import V2TestCase

class UnAthorizedGetTest(V2TestCase):
	
	def _run_200_test(self, username=VOID_VALUE, password=VOID_VALUE):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		tester.getTest(self.URL_json, username=username, password=password, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(self.URL_json)
		expectedValues.setValues(code=self.OK, body=self.default_return, lastModified=modifiedTime, 
								ifModifiedSinceError=self.NotModifiedSince, ifModifiedSinceSuccess=self.OK)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		
	def test_Server200IncorrectUsernameGetTestCase(self):
		self._run_200_test(username=self.incorrectUser)

	def test_Server200NoUsernameGetTestCase(self):
		self._run_200_test(username=self.noUser)

	#------------------------------
	
	def _run_400_test(self, username=VOID_VALUE, password=VOID_VALUE, body=None):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		body = body or self.default_return
		
		tester.getTest(self.URL_json, username=username, password=password, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(self.URL_json)
		expectedValues.setValues(code=self.Unauthorized, body=body, lastModified=modifiedTime)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read from URL')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		if body != self.void:
			self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		
	def test_Server401EmptyUsernameGetTestCase(self):
		self._run_400_test(username=self.emptyUser, body=self.void)
		
	def test_Server401IncorrectPasswordGetTestCase(self):
		self._run_400_test(password=self.incorrectPassword)
		
	def test_Server401EmptyPasswordGetTestCase(self):
		self._run_400_test(password=self.emptyPassword)
	
	def test_Server401NoPasswordGetTestCase(self):
		self._run_400_test(password=self.void)
	
if __name__ == '__main__':
	import unittest
	unittest.main()
