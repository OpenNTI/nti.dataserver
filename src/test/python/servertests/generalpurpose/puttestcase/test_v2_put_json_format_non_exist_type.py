'''
Created on Oct 10, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.puttestcase import PutTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2
from servertests.generalpurpose.utilities.url_formatter import JsonFormat

class V2Server200JsonFormatNonExistTypePutTestCase(PutTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2Server200JsonFormatNonExistTypePutTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_Server200JsonFormatNonExistTypePutTestCase(self):
		self.okPutTest(url=self.constants_object.URL_USER_NONEXIST_TYPE, urlGroup=self.constants_object.URL_USER_NONEXIST_TYPE_NO_ID, fmt=JsonFormat())
	
if __name__ == '__main__':
	import unittest
	unittest.main()