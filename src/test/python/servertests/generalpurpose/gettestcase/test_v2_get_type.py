'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.gettestcase import GetTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2
from servertests.generalpurpose.utilities.body_data_extracter import URL_Type

class V2Server200TypeGetTestCase(GetTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2Server200TypeGetTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_Server200TypeGetTestCase(self):
		self.okGetTest(url=self.constants_object.URL_USER_TYPE, bodyDataExtracter=URL_Type())
	
if __name__ == '__main__':
	import unittest
	unittest.main()