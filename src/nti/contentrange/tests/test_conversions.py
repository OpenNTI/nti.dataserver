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
from nti.contentrange import _convertrange
from nti.contentrange import contentrange
from nti.contentrange.tests import test_helpers
import json
import sys

import hamcrest
from hamcrest import assert_that, is_, none
from hamcrest.core.base_matcher import BaseMatcher

class ConversionTests(unittest.TestCase):
	START_TO_START = 0
	START_TO_END = 1
	END_TO_START = 2
	END_TO_END = 3
	BEFORE = -1
	EQUAL = 0
	AFTER = 1
	NO_CHECK = 0

	def setUp(self):
		self.doc1 = test_helpers.Document("""
		<p id="id">
			A single selected text node
		</p>
		""")
		self.doc2 = test_helpers.Document("""
		<p id="id">
			An<i> italic </i>word.
		</p>
		""")
		self.doc3 = test_helpers.Document("""
		<p id="id">
			This is the <i>first<img id="123"></img></i> sentence.
			<span>This is the<i> second </i>sentence.</span>
		</p>
		""")
		self.doc4 = test_helpers.Document ("""
		<body>
			<div id="ThisIdIsTheBest">
				<span id="12312312" data-non-anchorable="true">
					<p>text node 1</p>
					<span>
						<p>text node 2</p>
					</span>
					<div></div>
				</span>
			</div>
		</body>""")
		self.el1 = self.doc1.text_hunt("A single")
		self.el2 = self.doc2.text_hunt("An")
		self.el3 = self.doc2.text_hunt("word")
		self.doc3.focus = self.doc3.element_hunt("id","id")
		coords = [[3,0],[3,2],[1,1]]
		self.el4s = [self.doc3.downpath(x) for x in coords]
		self.ranges = [_domrange.Range(self.el1,0,self.el1,27),
					 _domrange.Range(self.el2,0,self.el3,6),
					 _domrange.Range(self.el4s[0],8,self.el4s[1],10),
					 _domrange.Range(self.el4s[2],0,self.el4s[1],10)]
		r1 = _domrange.Range()
		r1.start.set_before(self.doc4.downpath([0,0,0]))
		r1.end.set_after(self.doc4.downpath([0,0,2]))
		self.ranges.append(r1)

	def dom_to_contentrange_tests(self):
		self.solutions  =  [['A',27,'node',23,'id',None],
							['An',2,'word.',0,'id',None],
							['is the',6,'sentence.',0,'id',None],
							[None,'img'],
							[None,None,None,None,"ThisIdIsTheBest",None]]
		self.cr = test_helpers.range_conversion_check(self.ranges,self.solutions)

	def contentrange_to_dom_tests(self):
		self.bk_solutions = ['A single selected text node',
							'An italic word.',
							'the second sentence.',
							self.NO_CHECK]
		cr,bk = test_helpers.round_trip_check(self.ranges,None,self.bk_solutions)
		cpnull = contentrange.DomContentRangeDescription()
		cpbroken = cr[3]
		cpbroken.start.elementId="wegrhstrytjh"
		bkbroken = _convertrange.contentToDomRange(cpbroken,self.ranges[3].get_root())
		
		assert_that( str(bkbroken), is_( 'None' ) )

	def anchorability_tests(self):
		doc = test_helpers.Document("""
		<body>
			<div id="123">
				<span id="a1234567"></span>
				<span></span>
				<span id="MathJax-blahblah"></span>
				this is some text
				<span id="b1234567" data-non-anchorable="true"></span>
				<span id="ext-gen1223423"></span>
			</div>
		</body>""")
		for x,y in map(None,range(6),[True, False, False, True, False, False]):
			assert_that ( _convertrange.is_anchorable(doc.downpath([0,x])), is_( y ) )
		assert_that ( _convertrange.is_anchorable(doc.root), is_( False ) )
		assert_that ( _convertrange.is_anchorable( None ), is_( False ) )

		doc = test_helpers.Document("<body>123456<img></img></body>")
		assert_that ( _convertrange.is_anchorable(doc.root.childNodes[0]), is_( False ) )
		assert_that ( _convertrange.is_anchorable(doc.root.childNodes[1]), is_( False ) )

	def tests_copied_from_javascript(self):
		doc = test_helpers.Document("""
		<div id="123">
			<span>
				<p>This is some text</p>
			<span>
			<p>Also, this is more text</p>
			</span>
				<a></a>
			</span>
		</div>""")
		r = _domrange.Range(doc.downpath([0,0,0]),3,doc.downpath([0,0,0]),6)
		test_helpers.range_conversion_check(r,['This',17,None,None])

		doc = test_helpers.Document("""
		<div id="123">
			<span>
				<p id="xzy1232314">Once upon a time, there lived a BEAST!</p>
				<span>
					<p id="xzydasdasae2342">The beasts name was, NextThoughtASaurus!</p>
				</span>
			</span>
		</div>""")
		r = _domrange.Range(doc.downpath([0,0,0]),3,doc.downpath([0,1,0,0]),5)
		cr = _convertrange.domToContentRange(r)
		assert_that ( cr.end.role, is_( "end" ) )
		assert_that ( cr.end.ancestor.elementId,
			 is_( doc.downpath([0,1,0]).getAttribute("id") ) )
		assert_that ( len(cr.end.contexts) > 0, is_( True ) )

	def integration_tests(self):
		# Known potential failure to watch out for
		# Checking the common ancestor node resolves this inconsistency: 
		# quoting just one "This is some text" leaves the ancestor at the
		# paragraph level, while quoting two forces the converter to
		# traverse up to the common div
		doc = test_helpers.Document("""
		<body>
			<div id="123">
				<p id="45">This is some text.</p>
				<p id="67">This is some text.</p>
			</div>
		</body>""")
		r = _domrange.Range(doc.downpath([0,0,0]),0,doc.downpath([0,1,0]),18)
		cr, bk = test_helpers.round_trip_check(r)
		assert_that ( cr.ancestor.elementId, is_( "123" ) )

		# Element pointer there and back test
		doc = test_helpers.Document("""
		<div id="123">
			34
			<img id="456"></img>
			<p>Here is some text.</p>
			<span>789</span>
		</div>""")
		r = _domrange.Range(doc.root.childNodes[1],0,doc.root.childNodes[3],0)
		test_helpers.round_trip_check(r)

	def shifting_document_tests(self):
		original_doc = test_helpers.Document("""
		<div id="123">
			<p id="45">
				This is some somewhat but not particularly long text for readers
				 with short attention spans.
			</p>
			<p id="67">
				This is some more text containing many uninteresting words.
			</p>
		</div>""")
		# Only textnode in each paragraph
		p = [x.childNodes[0] for x in original_doc.root.childNodes]
		r = [_domrange.Range(p[0],13,p[0],47), _domrange.Range(p[0],13,p[1],22)]
		new_doc1 = test_helpers.Document("""
		<div id="123">
			<p id="intruder">Ugh. </p>
			<p id="45">
				This is some somewhat but probably not particularly long text for 
				readers with short attention spans. Here are some extra words. 
			</p>
			<img src="whackamole.jpg"></img>
			<p id="67">
				This is some more text containing many, many uninteresting words.
			</p>
		</div>
		""")
		sln1 = ["somewhat but probably not particularly long",
				"somewhat but probably not particularly long text for readers"
			 	" with short attention spans. Here are some extra words. This"
				" is some more text"]
		new_doc2 = test_helpers.Document("""
		<div id="123">
			<p id="intruder">Ugh. </p>
			<p id="45">
				This is some somewhat but probably not particularly long text
				 for readers with short attention spans.
			</p>
			<img src="whackamole.jpg"></img>
			<span> Here are some extra words in a span. </span>
			<p id="67">
				This is some more text containing many, many uninteresting words.
			</p>
		</div>""")
		# Known bug; should be "somewhat but probably not particularly long"
		sln2 = ["somewhat but probably not particularly long",
				"somewhat but probably not particularly long text for readers"
				" with short attention spans. Here are some extra words in a"
				" span. This is some more text"]
		test_helpers.round_trip_check(r,new_doc1,sln1)
		test_helpers.round_trip_check(r,new_doc2,sln2)
