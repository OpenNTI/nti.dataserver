import time
import unittest

from nti.contentsearch.tests import phrases
from nti.contentsearch.contenttypes import Note

from whoosh.filedb.filestore import RamStorage

class TestNotes(unittest.TestCase):

	now = time.time()

	def get_notes(self):
		result = list()
		for x in xrange(10):
			d = {}
			d['CollectionID'] = 'prealgebra'
			d['OID'] = '0x' + str(x).encode('hex')
			d['ContainerId'] = "aops-" + str(x)
			d['Creator'] = 'ntdev@nextthought.com'
			d["Last Modified"] = self.now
			d['text'] = phrases[x]
			d['sharedWith'] = ['cutz@nextthought.com', 'cs@nt.com']
			d['references'] = ['aops-main']
			d['id'] = x
			result.append(d)
		return result

	def create_note_index(self):
		note = Note()
		schema = note.get_schema()
		idx = RamStorage().create_index(schema)

		w = idx.writer()
		for d in self.get_notes():
			note.index_content(w, d, auto_commit=False)
		w.commit()

		return (note, idx)

	@unittest.expectedFailure
	def test_add_and_search(self):

		note, idx = self.create_note_index()
		with idx.searcher() as s:
			d = note.search(s, "alpha")

			self.assertEqual(d['Hit Count'], 1)
			self.assertEqual(d['Query'], "alpha")
			self.assertEqual(d['Last Modified'], self.now)

			items = d['Items']
			self.assertEqual(len(items), 1)

			item = items['0x32']
			self.assertEqual(item['Snippet'], 'ALPHA beta')
			self.assertEqual(item['Last Modified'], self.now)
			self.assertEqual(item['Type'], 'Note')
			self.assertEqual(item['Class'], 'Hit')

	@unittest.expectedFailure
	def test_update(self):

		note, idx = self.create_note_index()

		d = self.get_notes()[0]
		d['text'] = "Pillow brown"

		newtime = time.time()
		d["Last Modified"] = newtime

		note.update_content(idx.writer(), d)

		with idx.searcher() as s:
			d = note.search(s, "pillow")
			self.assertEqual(d['Hit Count'], 1)
			self.assertEqual(d['Last Modified'], newtime)

			item = d['Items']['0x30']
			self.assertEqual(item['Snippet'], 'PILLOW brown')

	def test_delete(self):

		note, idx = self.create_note_index()

		d = self.get_notes()[0]
		note.delete_content(idx.writer(), d)

		with idx.searcher() as s:
			d = note.search(s, "pillow")
			self.assertEqual(d['Hit Count'], 0)

	@unittest.expectedFailure
	def test_suggest(self):

		note, idx = self.create_note_index()
		with idx.searcher() as s:
			d = note.suggest(s, "re")
			self.assertEqual(d['Hit Count'], 1)
			self.assertEqual(d['Last Modified'], 0)
			item = d['Items'][0]
			self.assertEqual(item, 'red')

if __name__ == '__main__':
	unittest.main()
