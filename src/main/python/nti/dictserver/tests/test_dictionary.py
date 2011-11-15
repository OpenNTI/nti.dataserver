#!/usr/bin/env python2.7

import hamcrest
from nti.appserver import tests
from nti.dictserver import ChromeDictionary

class TestDictionary(tests.ConfiguringTestBase): 

	#This test makes sure that when a dict is constructed without a lookup path,
	#or other bad path of some sort, it fails
	def test_badConstructorValues( self ):
		self.assertRaises(LookupError, ChromeDictionary, '')
		self.assertRaises(TypeError, ChromeDictionary)
		self.assertRaises(TypeError, ChromeDictionary, None)
	
