import os
import json
import unittest
from datetime import datetime

from nti.contentsearch.contenttypes import echo
from nti.contentsearch.contenttypes import get_content
from nti.contentsearch.contenttypes import get_datetime
from nti.contentsearch.contenttypes import get_keywords
from nti.contentsearch.contenttypes import get_text_from_mutil_part_body

class TestContentTypes(unittest.TestCase):
	
	def _load_json(self, name = "message_info.json"):
		result = os.path.join(os.path.dirname(__file__), name)
		with open(result, "r") as f:
			result = json.load(f)
		return result

	def test_echo(self):
		self.assertEqual('', echo(None))
		self.assertEqual('', echo(''))
		self.assertEqual('None', echo('None'))
	
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

if __name__ == '__main__':
	unittest.main()
