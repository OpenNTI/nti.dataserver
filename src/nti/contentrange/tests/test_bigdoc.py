#!/usr/bin/env python
# -*- coding: utf-8 -*-
                                                                                         
"""                                                                                       
$Id$                                                                                      
"""

from __future__ import print_function
import unittest
import xml.dom
import xml.dom.minidom
from nti.contentrange import _domrange
from nti.contentrange import _convertrange
from nti.contentrange.tests import test_helpers
from nti.contentrange import contentrange
import json, re
import sys
import os
import pkg_resources

import hamcrest
from hamcrest import assert_that, is_, none
from hamcrest.core.base_matcher import BaseMatcher

class BigDocTests(unittest.TestCase):

	def setUp(self):
		self.main = str(pkg_resources.resource_string( \
						'nti.contentrange.tests','bigdoc.html'))
		self.main = "".join(i for i in self.main if ord(i) < 128)
		self.main = re.sub('\&\#8[0-9][0-9][0-9]',' ',self.main)
		self.main = self.main.replace('\n',' ')
	def test1(self):
		bigdoc = test_helpers.Document(self.main)
		# Useful tool for making test cases; set navigator to True to activate
		# Use 0,1,2, etc to navigate to a child, b to go back to parent
		cur_node = bigdoc.root
		navigator = False
		while navigator:
			for c in cur_node.childNodes:
				sys.stderr.write(str(c)+'\n')
			val = raw_input()
			if val == 'b': cur_node = cur_node.parentNode
			else:
				if cur_node.nodeType == cur_node.TEXT_NODE:
					sys.stderr.write('Text: ' + cur_node.data[:250]+'\n')
				else:
					cur_node = cur_node.childNodes[int(val)]
		bigdoc.focus = bigdoc.downpath([3,3,1,1,1,1,1,1])
		n1,o1 = bigdoc.text_hunt("chorable content is modeled",offset=True)
		n2,o2 = bigdoc.text_hunt("Anchored",n1.parentNode,True,-1)
		n3,o3 = bigdoc.text_hunt("selections/ranges",offset=True,querypos=10)
		n4,o4 = bigdoc.text_hunt("specific ranges of con",offset=True,querypos=8)
		n5,o5 = bigdoc.text_hunt("effect. This",offset=True,querypos=-5)
		n6,o6 = bigdoc.text_hunt("outside",offset=True,querypos=6) #1st occurrence
		n7,o7 = bigdoc.text_hunt("Dom Range Specification",bigdoc.downpath([7]),True,9)
		n8,o8 = bigdoc.downpath([7,5,0,0,19]), 0 # Blank textnode
		n9,o9 = bigdoc.text_hunt("TextDomContentPointer",offset=True)
		n10,o10 = bigdoc.text_hunt("be nil.",offset=True,querypos=-1)
		r = [_domrange.Range(n1,o1,n2,o2),
			_domrange.Range(n2,o2,n3,o3),
			_domrange.Range(n3,o3,n4,o4),
			_domrange.Range(n5,o5,n6,o6),
			_domrange.Range(n7,o7,n8,o8),
			_domrange.Range(n9,o9,n10,o10)]
		solutions = [['anchorable', None, 'Anchored', None],
					['Anchored', None, 'selections/ranges', None],
					['selections/ranges', None, 'specific ranges', None],
					['effect. This', None, 'outside', None],
					[],
					['TextDomContentPointer', None, 'nil.', None]]
		ct, br = test_helpers.round_trip_check(r)
		# Main context in ct[4] will be blank, secondaries will be the distinguishing factor
		assert_that (True in ["Notice that" in c.contextText for c in ct[4].end.contexts], True )
