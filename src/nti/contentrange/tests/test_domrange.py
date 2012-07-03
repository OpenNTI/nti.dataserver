import unittest
import xml.dom
import xml.dom.minidom
from nti.contentrange import _domrange
import json

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
		document_string = """
		<table>
			<tr>
				<td>
					<p>123</p>
					<p>456</p>
				</td>
				<td>
					<ul>
						<li>1</li>
						<li>2</li>
						<li>3</li>
					</ul>
				</td>
			</tr>
			<tr>
				<td>
					<img src="123.png"></img>
				</td>
				<td>
					<p>123456789</p>
				</td>
			</tr>
		</table>
		""".replace('\n','').replace('	','')
		self.document = xml.dom.minidom.parseString(document_string)
		self.anc = self.document.getElementsByTagName("table")[0]
		# Element at 456
		self.el1 = self.anc.childNodes[0].childNodes[0].childNodes[1].childNodes[0]
		# Element at 456's parent
		self.el0 = self.anc.childNodes[0].childNodes[0].childNodes[1]
		# Element at <li>1</li>
		self.el2 = self.anc.childNodes[0].childNodes[1].childNodes[0].childNodes[0].childNodes[0]
		# Element at <td><img src...></td>
		self.el3 = self.anc.childNodes[1].childNodes[0]
		# Element at 123456789
		self.el4 = self.anc.childNodes[1].childNodes[1].childNodes[0].childNodes[0]
		self.r1 = _domrange.Range()
		self.r1.set_start(self.el1,2)
		self.r1.set_end(self.el3,0)
		self.r1ext = _domrange.Range()
		self.r1ext.set_start_before(self.el1)
		self.r1ext.set_end_after(self.el3)
		self.r2 = _domrange.Range()
		self.r2.set_start(self.el2,5)
		self.r2.set_end(self.el4,5)
		self.r2int = _domrange.Range()
		self.r2int.set_start_after(self.el2)
		self.r2int.set_end_before(self.el4)
		self.r3 = _domrange.Range()
		self.r3.set_start(self.el4,3)
		self.r3.set_end(self.el4,11)

	def test_point_comparisons(self):
		# The basics
		assert_that( self.r1.pointInside(self.el2,0), is_( True ) )
		assert_that (self.r1.pointInside(self.el4,5), is_( False ) )
		# Same node, different offsets
		assert_that (self.r2.pointInside(self.el4,3), is_( True ) )
		assert_that (self.r2.pointInside(self.el4,7), is_( False ) )
		# Node versus its own parent
		assert_that (self.r1.pointInside(self.el0,0), is_( False ) )
		assert_that (self.r1.pointInside(self.el0,1), is_( True ) )

	def test_range_comparisons(self):
		class RangeChecker(BaseMatcher):
			def __init__ (self, how, desired, r):
				self.how = how
				self.desired = desired
				self.r = r
			def _matches (self, other):
				self.result = other.compareBoundaryPoints(self.how,self.r) 
				return self.result == self.desired
			def describe_to (self, description):
				towords = {-1 : 'before', 0: 'equal', 1: 'after'}
				description.append_text('Expected ' + towords[self.desired] +
										', got ' + towords[self.result])
		def s2s_compare(desired,r):
			return RangeChecker(self.START_TO_START,desired,r)
		def s2e_compare(desired,r):
			return RangeChecker(self.START_TO_END,desired,r)
		def e2s_compare(desired,r):
			return RangeChecker(self.END_TO_START,desired,r)
		def e2e_compare(desired,r):
			return RangeChecker(self.END_TO_END,desired,r)
		# First starts before second
		assert_that( self.r1, is_( s2s_compare( self.BEFORE, self.r2 ) ) )
		# Two synonyms
		assert_that( self.r1, is_( e2s_compare( self.AFTER, self.r2 ) ) )
		assert_that( self.r2, is_( s2e_compare( self.BEFORE, self.r1 ) ) )
		# x = x
		assert_that( self.r1, is_( s2s_compare( self.EQUAL, self.r1 ) ) )
		# First ends before second
		assert_that( self.r1, is_( e2e_compare( self.BEFORE, self.r2 ) ) )
		# First against own exterior
		assert_that( self.r1, is_( s2s_compare( self.AFTER, self.r1ext ) ) )
		assert_that( self.r1ext, is_( s2s_compare( self.BEFORE, self.r1 ) ) )
		assert_that( self.r1ext, is_( e2e_compare( self.AFTER, self.r1 ) ) )
		assert_that( self.r1, is_( e2e_compare( self.BEFORE, self.r1ext ) ) )
		# Second against own interior
		assert_that( self.r2, is_( s2s_compare( self.BEFORE, self.r2int ) ) )
		assert_that( self.r2, is_( e2e_compare( self.AFTER, self.r2int ) ) )
		# Where offsets matter
		assert_that( self.r2, is_( e2s_compare( self.AFTER, self.r3 ) ) )
		assert_that( self.r2, is_( e2e_compare( self.BEFORE, self.r3 ) ) )

	def test_stringifies(self):
		assert_that( str(self.r1), is_( '6123' ) )
		assert_that( self.r2.stringify(), is_( '2312345' ) )
		assert_that( self.r3.stringify(), is_( '456789' ) )
		# End is not a text node
		self.r2.set_end_before(self.r3.end_node)
		assert_that( self.r2.stringify(), is_( '23' ) )
		self.r4 = _domrange.Range()
		self.r4.set_start(self.el3,0)
		self.r4.set_end(self.el4,4)
		# Start is not a text node
		assert_that( self.r4.stringify(), is_( '1234' ) )

	def test_collapses(self):
		self.r5 = _domrange.Range()
		self.r5.set_start(self.el2,2)
		self.r5.set_end(self.el1,2)
		assert_that( self.r1.collapsed, is_( False ) )
		assert_that( self.r2.collapsed, is_( False ) )
		assert_that( self.r5.collapsed, is_( True ) )
		self.r1.collapse(True)
		assert_that( self.r1.collapsed, is_( True ) )
		self.r2.collapse(False)
		assert_that( self.r2.collapsed, is_( True ) )
		assert_that( self.r2.stringify(), is_( '' ) )


