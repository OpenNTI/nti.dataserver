import unittest

from nti.contentsearch import QueryObject

from hamcrest import (assert_that, is_)

class TestContetSearch(unittest.TestCase):

	def test_queryobject_ctor(self):
		try:
			QueryObject(foo=u'dummy')
			self.fail('must specify a query term')
		except:
			pass
		
		qo = QueryObject(term=u'term')
		assert_that(qo.term, is_(u'term'))
		assert_that(qo.query, is_(u'term'))
		
		qo = QueryObject(query=u'query')
		assert_that(qo.term, is_(u'query'))
		assert_that(qo.query, is_(u'query'))

	def test_queryobject_properties(self):
		d = {k: '400' for k in QueryObject.__int_properties__}
		qo = QueryObject(query=u'query', username='nt', **d)
		for k in QueryObject.__int_properties__:
			assert_that(qo[k], is_(400))
		
		assert_that(qo.limit, is_(400))
		assert_that(qo.prefix, is_(400))
		assert_that(qo.maxchars, is_(400))
		assert_that(qo.maxdist, is_(400))
		assert_that(qo.surround, is_(400))
		assert_that(qo.username, is_(u'nt'))

if __name__ == '__main__':
	unittest.main()
