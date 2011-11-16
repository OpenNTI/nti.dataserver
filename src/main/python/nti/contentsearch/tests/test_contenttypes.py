import os
import json
import unittest

from nti.contentsearch.contenttypes import get_text_from_mutil_part_body

class TestContentTypes(unittest.TestCase):

	sample_transcript = None

	def _load_json(self, name = "message_info.json"):
		result = os.path.join(os.path.dirname(__file__), name)
		with open(result, "r") as f:
			result = json.load(f)
		return result

	def test_get_text_from_mutil_part_body(self):
		js = self._load_json()
		msg = get_text_from_mutil_part_body(js['Body'])
		self.assertEqual(u'Zanpakuto and Zangetsu', msg)

if __name__ == '__main__':
	unittest.main()
