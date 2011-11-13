from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonUnAuthorizedPutTest(V2TestCase):
	
	def _run_test(self, code, username):
		bde = URL_Default()
		tester = self.controller()
		expectedValues = URLFunctionality()
				
		oldGroupTime = tester.getLastModified(self.URL_post)
		tester.putTest(self.URL_json, data=self.postPut_info, username=username, bodyDataExtracter=bde, fmt=self.json)
		modifiedTimeID = tester.getLastModified(self.URL_json)
		modifiedTimeGrp = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=code, body=self.default_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bde.responseCode, expectedValues.responseCode, "supposed to not allow access to wrong user / bad access info")
		self.assertEqual(bde.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bde.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		
	def test_Server403JsonFormatIncorrectUsernamePutTestCase(self):
		self._run_test(code=self.Forbidden, username=self.incorrectUser)
		
	def test_Server403JsonFormatNoUsernamePutTestCase(self):
		self._run_test(code=self.Forbidden, username=self.noUser)
		
	def test_Server500JsonFormatEmptyUsernamePutTestCase(self):
		self._run_test(code=self.WrongType, username=self.emptyUser)
		
	# -----------------------------

	def _run_401_test(self, password):
		bde = URL_Default()
		tester = self.controller()
		expectedValues = URLFunctionality()
				
		oldGroupTime = tester.getLastModified(self.URL_post)
		tester.putTest(self.URL_json, data=self.postPut_info, password=password, bodyDataExtracter=bde, fmt=self.json)
		modifiedTimeID = tester.getLastModified(self.URL_json)
		modifiedTimeGrp = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.Unauthorized, body=self.default_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bde.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to put to URL')
		self.assertEqual(bde.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bde.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')

		
	def test_Server401JsonFormatIncorrectPasswordPutTestCase(self):
		self._run_401_test(password=self.incorrectPassword)

	def test_Server401JsonFormatEmptyPasswordPutTestCase(self):
		self._run_401_test(password=self.emptyPassword)

	def test_Server401JsonFormatNoPasswordPutTestCase(self):
		self._run_401_test(password=self.noPassword)

if __name__ == '__main__':
	import unittest
	unittest.main()
