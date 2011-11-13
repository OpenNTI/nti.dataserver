from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control.v3 import V3TestCase

class StandardJsonPutTest(V3TestCase):

	def _run_test(self, data, fmt=NoFormat()):
		tester= self.controller_quiz()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		oldGroup = tester.getBody(self.URL_post)
		modifiedTimeOld	 = tester.getLastModified(self.URL_post)
		tester.putTest(self.URL_json, data=self.put_questions, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID = tester.getLastModified(self.URL_json)
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.OK, body=self.put_answer)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime expected to be greater that modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'not supposed to be equal')
		
	def test_Server200DefaultPutTestCase(self):
		self._run_test(self.put_questions)

	def test_Server200JsonFormatPutTestCase(self):
		self._run_test(self.put_questions, fmt=self.json)
		
	def test_Server200BadIDPutTestCase(self):
		self._run_test(self.put_questions_bad_ID)

if __name__ == '__main__':
	import unittest
	unittest.main()
