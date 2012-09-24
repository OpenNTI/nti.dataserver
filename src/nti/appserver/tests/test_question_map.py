#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import nti.tests
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_property

import json

from .._question_map import QuestionMap, _populate_question_map_from_text

setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.appserver,) )
tearDownModule = nti.tests.module_teardown

ASSM_ITEMS = {
	'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion': {'Class': 'Question',
																	  'MimeType': 'application/vnd.nextthought.naquestion',
																	  'NTIID': 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion',
																	  'content': '<a name="testquestion"></a> Arbitrary content goes here.',
																	  'parts': [{'Class': 'SymbolicMathPart',
																				 'MimeType': 'application/vnd.nextthought.assessment.symbolicmathpart',
																				 'content': 'Arbitrary content goes here.',
																				 'explanation': '',
																				 'hints': [],
																				 'solutions': [{'Class': 'LatexSymbolicMathSolution', 'MimeType': 'application/vnd.nextthought.assessment.mathsolution',
																								'value': 'Some solution','weight': 1.0}]}]},
	'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.set.testset': {'Class': 'QuestionSet',
																	 'MimeType': 'application/vnd.nextthought.naquestionset',
																	 'NTIID': 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.set.testset',
																	 'questions': [{'Class': 'Question',
																					'MimeType': 'application/vnd.nextthought.naquestion',
																					'NTIID': 'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion',
																					'content': '<a name="testquestion"></a> Arbitrary content goes here.',
																					'parts': [{'Class': 'SymbolicMathPart',
																							   'MimeType': 'application/vnd.nextthought.assessment.symbolicmathpart',
																							   'content': 'Arbitrary content goes here.',
																							   'explanation': '',
																							   'hints': [],
																							   'solutions': [{'Class': 'LatexSymbolicMathSolution', 'MimeType': 'application/vnd.nextthought.assessment.mathsolution',
																											  'value': 'Some solution', 'weight': 1.0}]}]}]}
}

SECTION_ONE = {
	'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.section_one',
	'filename': 'tag_nextthought_com_2011-10_testing-HTML-temp_section_one.html',
	'href': 'tag_nextthought_com_2011-10_testing-HTML-temp_section_one.html',
	'AssessmentItems': ASSM_ITEMS,
	}

CHAPTER_ONE = {
	'Items': {SECTION_ONE['NTIID']: SECTION_ONE	},
	'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.chapter_one',
	'filename': 'tag_nextthought_com_2011-10_testing-HTML-temp_chapter_one.html',
	'href': 'tag_nextthought_com_2011-10_testing-HTML-temp_chapter_one.html'
	}

ROOT = {
	'Items': { CHAPTER_ONE['NTIID']: CHAPTER_ONE },
	'NTIID': 'tag:nextthought.com,2011-10:testing-HTML-temp.0',
	'filename': 'index.html',
	'href': 'index.html'}

ASSM_JSON_W_SET = {
	'Items': { ROOT['NTIID']: ROOT },
	'href': 'index.html'
	}

ASSM_STRING_W_SET = json.dumps( ASSM_JSON_W_SET )

def test_create_question_map_captures_set_ntiids(index_string=ASSM_STRING_W_SET):
	class MockEntry(object):
		def make_sibling_key( self, key ):
			return key
	question_map = QuestionMap()
	_populate_question_map_from_text( question_map, index_string, MockEntry() )


	assm_items = question_map.by_file['tag_nextthought_com_2011-10_testing-HTML-temp_chapter_one.html']

	assert_that( assm_items, has_length( 2 ) ) # one question, one set
	assert_that( assm_items[1], has_property( 'ntiid',  'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion' ) )
	assert_that( assm_items[1], has_property( '__name__',  'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion' ) )
	assert_that( assm_items[0], has_property( 'ntiid',  'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.set.testset' ) )
	assert_that( assm_items[0], has_property( '__name__',  'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.set.testset' ) )

	qset = assm_items[0]
	qset_question = qset.questions[0]

	assert_that( qset_question, is_( assm_items[1] ) )
	assert_that( qset_question, has_property( 'ntiid',  'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion' ) )
	assert_that( qset_question, has_property( '__name__',  'tag:nextthought.com,2011-10:testing-NAQ-temp.naq.testquestion' ) )


	assert_that( question_map[qset_question.ntiid], is_( qset_question ) )
	assert_that( question_map[qset_question.ntiid], is_( assm_items[1] ) )
	assert_that( question_map[qset.ntiid], is_( qset ) )

def test_create_question_map_nested_level_with_no_filename():

	section_one = SECTION_ONE.copy()
	del section_one['filename']
	chapter_one = CHAPTER_ONE.copy()
	chapter_one['Items'][section_one['NTIID']] = section_one

	root = ROOT.copy()
	root['Items'][chapter_one['NTIID']] = chapter_one

	assm_json = {
		'Items': { root['NTIID']: root },
		'href': 'index.html'
	}

	assm_string = json.dumps( assm_json )

	test_create_question_map_captures_set_ntiids( assm_string )


def test_create_question_map_nested_two_level_with_no_filename():

	section_one = SECTION_ONE.copy()
	del section_one['filename']
	interloper = { 'NTIID': 'foo',
				   'Items': { section_one['NTIID']: section_one } }

	chapter_one = CHAPTER_ONE.copy()
	chapter_one['Items'] = {interloper['NTIID']: interloper}

	root = ROOT.copy()
	root['Items'][chapter_one['NTIID']] = chapter_one

	assm_json = {
		'Items': { root['NTIID']: root },
		'href': 'index.html'
	}

	assm_string = json.dumps( assm_json )

	test_create_question_map_captures_set_ntiids( assm_string )
