'''
Created on Oct 25, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.puttestcase import PutTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2

class V2ServerIncrementingIDsTestCase(PutTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2ServerIncrementingIDsTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_IncrementingIDsTestCase(self):
		self.assertEqual(int(self.incrementingIDs[0]) + 1, int(self.incrementingIDs[1]), 'The ids when posting to the server are not incrementing properly')
	
if __name__ == '__main__':
	import unittest
	unittest.main()