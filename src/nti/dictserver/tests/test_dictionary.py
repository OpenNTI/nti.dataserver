#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: __init__.py 8519 2012-06-29 22:00:46Z jason.madden $
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import is_
from hamcrest import none

import anyjson as json
from zope import component

import nti.tests
from nose.tools import assert_raises
import fudge

from nti.dictserver.storage import UncleanSQLiteJsonDictionaryTermStorage as Storage
from nti.dictserver.storage import JsonDictionaryTermDataStorage as JsonDictionary
from nti.dictserver import lookup
from nti.dictserver.term import DictionaryTerm as WordInfo


class TestDictionary(nti.tests.ConfiguringTestBase):

	# this test makes sure that when a dict is constructed without a lookup path,
	# or other bad path of some sort, it fails
	def test_badConstructorValues( self ):
		assert_raises(ValueError, Storage, '')
		assert_raises(TypeError, Storage)
		assert_raises(TypeError, Storage, None)

	@fudge.patch( 'sqlite3.connect' )
	def test_no_lookup( self, sqlite3_connect ):
		fake_conn = sqlite3_connect.expects_call().returns_fake()
		fake_cur = fake_conn.expects('execute').with_arg_count( 2 ).returns_fake( )
		fake_cur.expects( 'fetchone' ).returns( (None,) )
		fake_cur.expects( 'close' )
		json_dict = Storage( ":memory:" )

		val = json_dict.lookup( 'word' )
		assert_that( val, is_not( none() ) )

	@fudge.patch( 'sqlite3.connect' )
	def test_does_lookup( self, sqlite3_connect ):
		fake_conn = sqlite3_connect.expects_call().returns_fake()
		fake_conn.expects( 'close' )
		fake_cur = fake_conn.expects('execute').with_arg_count( 2 ).returns_fake( )
		fake_cur.expects( 'fetchone' ).returns( ('text',) )
		fake_cur.expects( 'close' )
		json_dict = Storage( ":memory:" )

		val = json_dict.lookup( 'word' )
		assert_that( val, is_( 'text' ) )

		json_dict.close()

	@fudge.patch( 'sqlite3.connect' )
	def test_lookup_through_api( self, sqlite3_connect ):
		fake_conn = sqlite3_connect.expects_call().returns_fake()
		fake_conn.expects( 'close' )
		fake_cur = fake_conn.expects('execute').with_arg_count( 2 ).returns_fake( )
		defn = {'meanings': [{'content': 'Content',
							  'examples': ['ex1'],
							  'type': 'noun' } ],
				'synonyms': ['s1']
				}
		fake_cur.expects( 'fetchone' ).returns( (json.dumps( defn ),) )
		fake_cur.expects( 'close' )
		storage = Storage( ":memory:" )
		json_dict = JsonDictionary( storage )
		component.provideUtility( json_dict )
		val = lookup( 'word' )

		assert_that( val, is_( WordInfo ) )
		assert_that( val.toXMLString(), is_not( none() ) )
		storage.close()

	@fudge.patch( 'sqlite3.connect' )
	def test_lookup_bad_data_through_api( self, sqlite3_connect ):
		fake_conn = sqlite3_connect.expects_call().returns_fake()
		fake_conn.expects( 'close' )
		fake_cur = fake_conn.expects('execute').with_arg_count( 2 ).returns_fake( )
		fake_cur.expects( 'fetchone' ).returns( ('CANNOT LOAD',) )
		fake_cur.expects( 'close' )
		storage = Storage( ":memory:" )
		json_dict = JsonDictionary( storage )
		component.provideUtility( json_dict )
		val = lookup( 'word' )

		assert_that( val, is_( WordInfo ) )

		storage.close()
