from __future__ import print_function, unicode_literals
		
import time 
import datetime
import unittest						  

from repoze.catalog import query as repquery

from nti.contentsearch import _repoze_whoosh_convert

from hamcrest import assert_that, is_, any_of
from hamcrest.core.base_matcher import BaseMatcher

class isLikeMatcher(BaseMatcher):														
	def __init__ (self, string):														   
		self.string = string															  
	def _matches (self, other):														   
		return self.string.replace(' ','') == other.replace(' ','')
	def describe_to (self, description):												  
		description.append_text(self.string)
def is_like(string):
	return isLikeMatcher(string)

class RepozeWhooshConversionTests(unittest.TestCase):

	def setUp(self):
		self.q = _repoze_whoosh_convert.QueryConverter()

	def test_equality_and_contains(self):
		query = repquery.Eq('author','Bob')
		assert_that(self.q.convert_query(query),
				any_of( is_('author:Bob'), is_("author:'Bob'")))
		query = repquery.Eq('author','Bob Lastname')
		assert_that(self.q.convert_query(query),
				is_("author:'Bob Lastname'"))
		query = repquery.Eq('age',45)
		assert_that(self.q.convert_query(query),
				is_("age:45"))
		query = repquery.NotEq('author','Myleast Favorite')
		assert_that(self.q.convert_query(query),
				is_like("NOT (author:'Myleast Favorite')"))
		query = repquery.Contains('author','e')
		assert_that(self.q.convert_query(query),
				any_of( is_("author:*e*"), is_("author:'*e*'")))
		query = repquery.DoesNotContain('author','e')
		assert_that(self.q.convert_query(query),
				any_of(is_like("NOT(author:*e*)"), is_like("NOT (author:'*e*')")))

	def test_numerical_comparisons(self):
		query = repquery.Lt('age',60)
		assert_that(self.q.convert_query(query),
				any_of(is_("age:<60"),is_like("age:{TO 60}")))
		query = repquery.Gt('age',30)
		assert_that(self.q.convert_query(query),
				any_of(is_("age:>30"),is_like("age:{30 TO}")))
		query = repquery.Ge('age',31)
		assert_that(self.q.convert_query(query),
				any_of(is_("age:>=31"),is_like("age:[31 TO}")))
		query = repquery.Le('age',59)
		assert_that(self.q.convert_query(query),
				any_of(is_("age:<=59"),is_like("age:{TO 59]")))

	def test_booleans(self):
		left = repquery.Eq('author','Bob Lastname')
		right = repquery.Eq('age','45')
		query = repquery.And(left,right)
		assert_that(self.q.convert_query(query),
				is_like("author:'Bob Lastname' AND age:45"))
		query = repquery.Or(left,right)
		assert_that(self.q.convert_query(query),
				is_like("author:'Bob Lastname' OR age:45"))
		center = repquery.Eq('book','Default Title')
		query = repquery.And(left,center,right)
		assert_that(self.q.convert_query(query), 
			 	is_like("author:'Bob Lastname' AND book:'Default Title' AND age:45"))
		query = repquery.Or(left,center,right)
		assert_that(self.q.convert_query(query),
			 	is_like("author:'Bob Lastname' OR book:'Default Title' OR age:45"))
		query = repquery.And(repquery.Or(left,center),right)
		assert_that(self.q.convert_query(query),
			 	is_like("(author:'Bob Lastname' OR book:'Default Title') AND age:45"))

	def test_date_conversions(self):
		self.uq = _repoze_whoosh_convert.QueryConverter('default')
		query = repquery.Gt('last_modified',time.mktime(datetime.datetime(2012,3,14).timetuple()))
		assert_that(self.uq.convert_query(query), 
				is_like("last_modified:{14 march 2012 TO}"))

	def test_index_translations(self):
		query = repquery.Lt('LAST_MODIFIED',2147483647)
		assert_that(self.q.convert_query(query)[:14], is_("last_modified:"))
		query = repquery.Eq('NTIID','hi-im-an-id-085175')
		assert_that(self.q.convert_query(query)[:6], is_("ntiid:"))
		query = repquery.Eq('kw','keyword')
		assert_that(self.q.convert_query(query)[:9], is_("keywords:"))
