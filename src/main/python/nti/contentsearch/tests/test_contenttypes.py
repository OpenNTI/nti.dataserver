import os
import json
import unittest

from nti.contentsearch.contenttypes import echo
from nti.contentsearch.contenttypes import get_keywords
from nti.contentsearch.contenttypes import get_text_from_mutil_part_body

class TestContentTypes(unittest.TestCase):

	sample_transcript = None

	def _load_json(self, name = "message_info.json"):
		result = os.path.join(os.path.dirname(__file__), name)
		with open(result, "r") as f:
			result = json.load(f)
		return result

	def test_echo(self):
		self.assertEqual('', echo(None))
		self.assertEqual('', echo(''))
		self.assertEqual('None', echo('None'))
	
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
