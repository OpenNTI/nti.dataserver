'''
Created on Oct 10, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.puttestcase import PutTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2

class V2Server201JsonFormatNonExistIDPutTestCase(PutTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2Server201JsonFormatNonExistIDPutTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_Server201JsonFormatNonExistIDPutTestCase(self):
		self.successfulAddPutTestJsonFormat(url=self.constants_object.URL_USER_NONEXIST_ID)
	
if __name__ == '__main__':
	import unittest
	unittest.main()