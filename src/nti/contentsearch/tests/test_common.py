import os
import json
import unittest
import collections
from datetime import datetime

from hamcrest import assert_that, has_length

from nti.contentsearch.contenttypes import MessageInfo

from nti.contentsearch.common import echo
from nti.contentsearch.common import epoch_time
from nti.contentsearch.contenttypes import get_content
from nti.contentsearch.contenttypes import get_datetime
from nti.contentsearch.contenttypes import get_keywords
from nti.contentsearch.contenttypes import get_highlighted_content
from nti.contentsearch.contenttypes import get_text_from_mutil_part_body
from nti.contentsearch.common import merge_search_results
from nti.contentsearch.common import merge_suggest_results
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common  import empty_suggest_and_search_result

class TestCommon(unittest.TestCase):

	def _load_json(self, name = "message_info.json"):
		result = os.path.join(os.path.dirname(__file__), name)
		with open(result, "r") as f:
			result = json.load(f)
		return result

	def test_echo(self):
		self.assertEqual('', echo(None))
		self.assertEqual('', echo(''))
		self.assertEqual('None', echo('None'))

	def test_epoch_time(self):
		d = datetime.fromordinal(730920)
		self.assertEqual(1015826400.0, epoch_time(d))
		self.assertEqual(0, epoch_time(None))

	def test_get_datetime(self):
		f = 1321391468.411328
		s = '1321391468.411328'
		self.assertEqual(get_datetime(f), get_datetime(s))
		self.assert_(get_datetime() <= datetime.now())

	def test_get_content(self):
		self.assertEqual(u'', get_content(None))
		self.assertEqual(u'', get_content({}))
		self.assertEqual('Zanpakuto Zangetsu', get_content('Zanpakuto Zangetsu'))
		self.assertEqual('Zanpakuto Zangetsu', get_content('\n\tZanpakuto,Zangetsu'))
		self.assertEqual('Zangetsu', get_content('<html><b>Zangetsu</b></html>'))
		self.assertEqual('orange-haired', get_content('orange-haired'))

		self.assertEqual('U.S.A. vs Japan', get_content('U.S.A. vs Japan'))
		self.assertEqual('$12.45', get_content('$12.45'))
		self.assertEqual('82%', get_content('82%'))

		u = unichr(40960) + u'bleach' + unichr(1972)
		self.assertEqual('bleach', get_content(u))

	def test_get_keywords(self):
		self.assertEqual('', get_keywords(None))
		self.assertEqual('', get_keywords(''))
		self.assertEqual('Zanpakuto,Zangetsu', get_keywords(('Zanpakuto', 'Zangetsu')))

	def test_get_text_from_mutil_part_body(self):
		js = self._load_json()
		msg = get_text_from_mutil_part_body(js['Body'])
		self.assertEqual(u'Zanpakuto and Zangetsu', msg)
		self.assertEqual('Soul Reaper', get_text_from_mutil_part_body('Soul Reaper'))

	def test_get_highlighted_content(self):
		text = unicode(get_content("""
		An orange-haired high school student, Ichigo becomes a "substitute Shinigami (Soul Reaper)"
		after unintentionally absorbing most of Rukia Kuchiki's powers
		"""))
		self.assertEqual('An orange-haired high school student ICHIGO becomes a substitute Shinigami Soul Reaper after unintentionally', get_highlighted_content('ichigo', text))
		self.assertEqual('ICHIGO becomes', get_highlighted_content('ichigo', text, surround=5))
		self.assertEqual('high school student Ichigo becomes a substitute SHINIGAMI Soul', get_highlighted_content('shinigami', text, maxchars=10))
		self.assertEqual('RUKIA', get_highlighted_content('rukia', text, maxchars=10, surround=1))

	def _check_empty(self, d, query):
		self.assert_(isinstance(d, collections.Mapping))
		self.assertEqual(query, d['Query'])
		self.assertEqual(0, d['Hit Count'])
		self.assertEqual(0, d['Last Modified'])

	def test_empty_search_result(self):
		d = empty_search_result('myQuery')
		self._check_empty(d, 'myQuery')
		self.assertEqual({}, d['Items'])

	def test_empty_suggest_result(self):
		d = empty_suggest_result('myQuery')
		self._check_empty(d, 'myQuery')
		assert_that( d['Items'], has_length(0) )


	def test_empty_suggest_and_search_result(self):
		d = empty_suggest_and_search_result('myQuery')
		self._check_empty(d, 'myQuery')
		self.assertEqual({}, d['Items'])
		self.assertEqual([], d['Suggestions'])

	def test_merge_search_results(self):
		a = {'Last Modified': 1, 'Items':{'a':1}}
		b = {'Last Modified': 2, 'Items':{'b':2}}
		m = merge_search_results(a, b)
		self.assertEqual(2, m['Last Modified'])
		self.assertEqual({'a':1, 'b':2}, m['Items'])
		self.assertEqual(2, m['Hit Count'])

		a = {'Last Modified': 1, 'Items':{'a':1}}
		b = {'Items':{'b':2}}
		m = merge_search_results(a, b)
		self.assertEqual(1, m['Last Modified'])

		a = {'Items':{'a':1}}
		b = {'Last Modified': 3, 'Items':{'b':2}}
		m = merge_search_results(a, b)
		self.assertEqual(3, m['Last Modified'])

		a = None
		b = {'Last Modified': 3, 'Items':{'b':2}}
		m = merge_search_results(a, b)
		self.assertEqual(b, m)

		a = {'Last Modified': 3, 'Items':{'b':2}}
		b = None
		m = merge_search_results(a, b)
		self.assertEqual(a, m)

		m = merge_search_results(None, None)
		self.assertEqual(None, m)

	def test_merge_suggest_results(self):
		a = {'Last Modified': 4, 'Items':['a']}
		b = {'Last Modified': 2, 'Items':['b','c']}
		m = merge_suggest_results(a, b)
		self.assertEqual(4, m['Last Modified'])
		self.assertEqual(['a','c', 'b'], m['Items'])
		self.assertEqual(3, m['Hit Count'])

		a = {'Last Modified': 1, 'Items':['a']}
		b = {'Items':['b']}
		m = merge_suggest_results(a, b)
		self.assertEqual(1, m['Last Modified'])
		self.assertEqual(['a','b'], m['Items'])

		a = {'Items':['a']}
		b = {'Last Modified': 3, 'Items':['b']}
		m = merge_suggest_results(a, b)
		self.assertEqual(3, m['Last Modified'])

		a = None
		b = {'Last Modified': 3, 'Items':['b']}
		m = merge_suggest_results(a, b)
		self.assertEqual(b, m)

		a = {'Last Modified': 3, 'Items':['c']}
		b = None
		m = merge_suggest_results(a, b)
		self.assertEqual(a, m)

		m = merge_suggest_results(None, None)
		self.assertEqual(None, m)

	def test_message_info(self):
		js = self._load_json()
		mi = MessageInfo()
		d = mi.get_index_data(js)
		self.assertEqual('tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x82:53657373696f6e73', d['containerId'])
		self.assertEqual('troy.daley@nextthought.com', d['creator'])
		self.assertEqual('tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73', d['oid'])
		self.assertEqual('tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73', d['ntiid'])
		self.assertEqual('Zanpakuto and Zangetsu', d['content'])
		self.assertEqual('troy.daley@nextthought.com,carlos.sanchez@nextthought.com', d['sharedWith'])
		self.assertEqual('Zanpakuto and Zangetsu', d['quick'])
		self.assertEqual('0d7ba380e77241508204a9d737625e04', d['id'])
		self.assertEqual('DEFAULT', d['channel'])
		self.assertEqual(datetime(2011, 11, 15, 15, 11, 8, 411328), d['last_modified'])

if __name__ == '__main__':
	unittest.main()
