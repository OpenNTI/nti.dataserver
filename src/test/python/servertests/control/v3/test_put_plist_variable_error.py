from url_functionality import URL_Default
from url_functionality import URLFunctionality
from servertests.control.v3 import V3TestCase

class VariableErrorJsonPutTests(V3TestCase):

	def _run_test(self, URL, data, code, body, string, password=None):
		obj = URLFunctionality()
		tester	= self.controller_quiz()
		bodyDataExtracter = URL_Default()
		
		password = password or self.password
		obj.setValues(code=code, body=body)
		
		modifiedTimeOld	= tester.getLastModified(self.URL_post)
		tester.putTest(URL, data=data, password=password, bodyDataExtracter=bodyDataExtracter, fmt=self.plist)
		modifiedTimeID = tester.getLastModified(URL, fmt=self.plist)
		modifiedTime = tester.getLastModified(self.URL_post)
		
		self.assertEqual(bodyDataExtracter.responseCode, obj.responseCode, \
						(bodyDataExtracter.responseCode, obj.responseCode, 'response code supposed to be ' + string))
		
		self.assertEqual(bodyDataExtracter.body, obj.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		if (obj.responseCode == self.SuccessfulAdd):
			self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeOld')
		else:
			self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeOld')

	def test_Server401JsonFormatIncorrectPasswordPutTestCase(self):
		self._run_test(	self.URL_plist, data=self.put_questions, password=self.incorrectPassword,\
						code=self.Unauthorized, body=self.default_answer, string='Unauthorized')

	def test_Server201JsonFormatNonExsistantIDPutTestCase(self):
		self._run_test(	self.URL_NoID, data=self.put_questions, code=self.SuccessfulAdd,\
						body=self.put_answer, string='successful put')

	def test_Server500JsonFormatWrongDatatypePutTestCase(self):
		self._run_test(self.URL_plist, data=self.wrongInfo, code=self.WrongType, body=self.default_answer, string='WrongData')

if __name__ == '__main__':
	import unittest
	unittest.main()
