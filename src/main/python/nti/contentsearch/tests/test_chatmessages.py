import os
import json
import unittest

from hamcrest import (assert_that, is_)
from whoosh.filedb.filestore import RamStorage

from nti.contentsearch.contenttypes import MessageInfo

class TestChatMessages(unittest.TestCase):

	sample_transcript = None

	@classmethod
	def setUpClass(cls):
		tf = os.path.join(os.path.dirname(__file__), 'transcript.json')
		with open(tf, "r") as f:
			cls.sample_transcript = json.load(f)

	def create_index_from_transcript(self, transcript):
		cm = MessageInfo()
		schema = cm.get_schema()
		idx = RamStorage().create_index(schema)

		w = idx.writer()
		for m in transcript['Messages']:
			cm.index_content(w, m, auto_commit=False)
		w.commit()

		return (cm, idx)

	def test_add_and_search(self):
		cm, idx = self.create_index_from_transcript(self.sample_transcript)
		with idx.searcher() as s:
			self.assertEqual(s.doc_count(), 72)

			d = cm.search(s, "hacker")
			self.assertEqual(d['Hit Count'], 10)
			self.assertEqual(d['Query'], "hacker")

			items = d['Items']
			self.assertEqual(len(items), 10)

			item = items['0xd8:53657373696f6e73']
			self.assertEqual(item['Snippet'], 'Chicken HACKER')
			self.assertEqual(item['Last Modified'], 1318543995.504597)
			assert_that( item['Type'], is_( 'MessageInfo' ) )
			self.assertEqual(item['Class'], 'Hit')
			self.assertEqual(item["ID"], "06c35b96bae5458793c0c505f255f94b")


	def test_delete(self):

		cm, idx = self.create_index_from_transcript(self.sample_transcript)
		cm.delete_content(idx.writer(), '0xd8:53657373696f6e73')

		with idx.searcher() as s:
			self.assertEqual(s.doc_count(), 71)

if __name__ == '__main__':
	unittest.main()
