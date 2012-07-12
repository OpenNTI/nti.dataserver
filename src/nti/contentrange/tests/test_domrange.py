#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
"""

from __future__ import print_function, unicode_literals
import unittest
import xml.dom
import xml.dom.minidom
from nti.contentrange import _domrange
from nti.contentrange.tests import test_helpers
import json
import sys

import hamcrest
from hamcrest import assert_that, is_
from hamcrest.core.base_matcher import BaseMatcher

class DomTests(unittest.TestCase):

	START_TO_START = 0
	START_TO_END = 1
	END_TO_START = 2
	END_TO_END = 3
	BEFORE = -1
	EQUAL = 0
	AFTER = 1

	def setUp(self):
		self.doc = test_helpers.Document("""
		<table id="thetable">
			<tr id="firstrow">
				<td>
					<p>123</p>
					<p>456</p>
				</td>
				<td>
					<ul>
						<li>a</li>
						<li>b</li>
						<li>c</li>
					</ul>
				</td>
			</tr>
			<tr id="secondrow">
				<td>
					<img src="123.png"></img>
				</td>
				<td>
					<p>123456789</p>
				</td>
			</tr>
		</table>
		""")
		self.el = {s: self.doc.text_hunt(s) for s in ['456','a','b','c','123456789']}
		self.el1 = self.el['456'].parentNode
		self.el2 = self.doc.downpath([1,0])
		self.r  =  [_domrange.Range(self.el['456'],2,self.el2,0),
					_domrange.Range(),
					_domrange.Range(self.el['a'],5,self.el['123456789'],5),
					_domrange.Range(),
					_domrange.Range(self.el['123456789'],3,self.el['123456789'],11)]
		self.r[1].set_start_before(self.r[0].start.node)
		self.r[1].set_end_after(self.r[0].end.node)
		self.r[3].set_start_after(self.r[2].start.node)
		self.r[3].set_end_before(self.r[2].end.node)

	def test_point_comparisons(self):
		r = self.r
		comparisons = [[r[0], self.el['a'], 0, True],
						[r[0], self.el['123456789'], 5, False],
						# Same node, different offsets
						[r[2], self.el['123456789'], 3, True],
						[r[2], self.el['123456789'], 7, False],
						# Node versus its own parent
						[r[0], self.el1, 0, False],
						[r[0], self.el1, 1, True]]
		for c in comparisons: test_helpers.point_in_range_check(*c)

	def test_range_comparisons(self):
		r = self.r
						# First starts before second
		comparisons  = [(r[0],r[2],self.START_TO_START,self.BEFORE),
						# Two synonyms
						(r[0],r[2],self.END_TO_START,self.AFTER),
						(r[2],r[0],self.START_TO_END,self.BEFORE),
						# x = x
						(r[0],r[0],self.START_TO_START,self.EQUAL),
						# First ends before second
						(r[0],r[2],self.END_TO_END,self.BEFORE),
						# First against own exterior
						(r[0],r[1],self.START_TO_START,self.AFTER),
						(r[1],r[0],self.START_TO_START,self.BEFORE),
						(r[1],r[0],self.END_TO_END,self.AFTER),
						(r[0],r[1],self.END_TO_END,self.BEFORE),
						# Second against own interiot
						(r[2],r[3],self.START_TO_START,self.BEFORE),
						(r[2],r[3],self.END_TO_END,self.AFTER),
						# Where offsets matter
						(r[2],r[4],self.END_TO_START,self.AFTER),
						(r[2],r[4],self.END_TO_END,self.BEFORE)]
		for c in comparisons: test_helpers.range_comparison_check(*c)

	def test_stringifies(self):
		assert_that( str(self.r[0]), is_( '6abc' ) )
		assert_that( self.r[2].stringify(), is_( 'bc12345' ) )
		assert_that( self.r[4].stringify(), is_( '456789' ) )
		# End is not a text node
		self.r[2].set_end_before(self.r[4].end.node)
		assert_that( self.r[2].stringify(), is_( 'bc' ) )
		r = _domrange.Range(self.el2,0,self.el['123456789'],4)
		# Start is not a text node
		assert_that( r.stringify(), is_( '1234' ) )

	def test_collapses(self):
		r = _domrange.Range(self.el['a'],2,self.el['456'],2)
		assert_that( self.r[0].collapsed, is_( False ) )
		assert_that( self.r[2].collapsed, is_( False ) )
		assert_that( r.collapsed, is_( True ) )
		self.r[0].collapse(True)
		assert_that( self.r[0].collapsed, is_( True ) )
		self.r[2].collapse(False)
		assert_that( self.r[2].collapsed, is_( True ) )
		assert_that( self.r[2].stringify(), is_( '' ) )

