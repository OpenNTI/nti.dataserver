import os
import json
import unittest

from whoosh.filedb.filestore import RamStorage

from nti.contentsearch.contenttypes import Highlight

class TestHighlight(unittest.TestCase):

	sample_hightlight = None

	@classmethod
	def setUpClass(cls):
		tf = os.path.join(os.path.dirname(__file__), 'highlight.json')
		with open(tf, "r") as f:
			cls.sample_hightlight = json.load(f)

	def _create_index(self):
		hi = Highlight()
		schema = hi.get_schema()
		idx = RamStorage().create_index(schema)
		hi.index_content(idx.writer(), self.sample_hightlight)
		return (hi, idx)

	def test_add_and_search(self):
		cm, idx = self._create_index()
		
		with idx.searcher() as s:
			self.assertEqual(s.doc_count(), 1)

			d = cm.search(s, "divide")
			self.assertEqual(d['Hit Count'], 1)
			self.assertEqual(d['Query'], "divide")
			self.assertEqual(d['Last Modified'], 1321584477.793211)

			items = d['Items']
			self.assertEqual(len(items), 1)
			item = items['0x62:5573657273']
			
			self.assertEqual('Hit', item['Class'])
			self.assertEqual('Highlight', item['Type'])
			self.assertEqual('prealgebra', item['CollectionID'])
			self.assertEqual("0x62:5573657273", item["TargetOID"])
			self.assertEqual('multiply and DIVIDE In fact you may already', item['Snippet'])
			self.assertEqual('tag:nextthought.com,2011-07-14:AOPS-HTML-prealgebra-0', item['ContainerId'])


	def test_delete(self):
		cm, idx = self._create_index()
		cm.delete_content(idx.writer(), '0x62:5573657273')
		with idx.searcher() as s:
			self.assertEqual(s.doc_count(), 0)

if __name__ == '__main__':
	unittest.main()
