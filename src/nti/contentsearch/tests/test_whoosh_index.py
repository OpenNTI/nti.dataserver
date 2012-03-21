import os
import json
import unittest
from datetime import datetime

from whoosh.filedb.filestore import RamStorage

from nti.contentsearch._whoosh_index import Note
from nti.contentsearch._whoosh_index import Highlight
from nti.contentsearch._whoosh_index import MessageInfo
from nti.contentsearch._whoosh_index import get_datetime
from nti.contentsearch._whoosh_index import get_keywords
from nti.contentsearch._whoosh_index import get_text_from_mutil_part_body

from hamcrest import (assert_that, is_, has_entry, has_key, has_length)

class TestWhooshIndex(unittest.TestCase):

	@classmethod
	def setUpClass(cls):	
		path = os.path.join(os.path.dirname(__file__), 'highlight.json')
		with open(path, "r") as f:
			cls.highlight = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'note.json')
		with open(path, "r") as f:
			cls.note = json.load(f)
				
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)

	def test_get_datetime(self):
		f = 1321391468.411328
		s = '1321391468.411328'
		assert_that(get_datetime(f), is_(get_datetime(s)))

	def test_get_keywords(self):
		self.assertEqual('', get_keywords(None))
		self.assertEqual('', get_keywords(''))
		self.assertEqual('Zanpakuto,Zangetsu', get_keywords(('Zanpakuto', 'Zangetsu')))

	def test_get_text_from_mutil_part_body(self):
		msg = get_text_from_mutil_part_body(self.messageinfo['Body'])
		self.assertEqual(u'Zanpakuto and Zangetsu', msg)
		self.assertEqual('Soul Reaper', get_text_from_mutil_part_body('Soul Reaper'))

	def test_highlight_index_data(self):
		hi = Highlight()
		d = hi.get_index_data(self.highlight)
		assert_that(d, has_entry('containerId', 'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0' ))
		assert_that(d, has_entry('creator', 'carlos.sanchez@nextthought.com' ))
		assert_that(d, has_entry('oid', 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273' ))
		assert_that(d, has_entry('ntiid', 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273' ))
		assert_that(d, has_entry('content', 
			'You know how to add subtract multiply and divide In fact you may already know how to solve many of the '
			'problems in this chapter So why do we start this book with an entire chapter on arithmetic' ))
		assert_that(d, has_entry('last_modified', datetime(2012, 3, 16, 13, 22, 0, 967309)))
				
	def test_note_index_data(self):
		no = Note()
		d = no.get_index_data(self.note)
		assert_that(d, has_entry('containerId', 'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0' ))
		assert_that(d, has_entry('creator', 'carlos.sanchez@nextthought.com' ))
		assert_that(d, has_entry('oid', 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0860:5573657273' ))
		assert_that(d, has_entry('ntiid', 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0860:5573657273' ))
		assert_that(d, has_entry('content', 
			'All Waves Rise now and Become my Shield Lightning Strike now and Become my Blade'))
		assert_that(d, has_entry('last_modified', datetime(2012, 3, 16, 13, 23, 21, 926812)))
		
	def test_messageinfo_index_data(self):
		mi = MessageInfo()
		d = mi.get_index_data(self.messageinfo)
		assert_that(d, has_entry('containerId', 'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x82:53657373696f6e73' ))
		assert_that(d, has_entry('creator', 'troy.daley@nextthought.com' ))
		assert_that(d, has_entry('oid', 'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73' ))
		assert_that(d, has_entry('ntiid', 'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73' ))
		assert_that(d, has_entry('content', 'Zanpakuto and Zangetsu' ))
		assert_that(d, has_entry('sharedWith', 'troy.daley@nextthought.com,carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry('id', '0d7ba380e77241508204a9d737625e04'))
		assert_that(d, has_entry('channel', 'DEFAULT'))
		assert_that(d, has_entry('last_modified', datetime(2011, 11, 15, 15, 11, 8, 411328)))
		
	def test_index_highlight(self):
					
		hi = Highlight()
		schema = hi.get_schema()
		idx = RamStorage().create_index(schema)
		hi.index_content(idx.writer(), self.highlight)
		
		with idx.searcher() as s:
			self.assertEqual(s.doc_count(), 1)

			d = hi.search(s, "divide")
			assert_that(d, has_entry('Hit Count', 1))
			assert_that(d, has_entry('Query', 'divide'))
			assert_that(d, has_entry('Last Modified', 1331922120.967309))
			assert_that(d, has_key('Items'))
			
			items = d['Items']
			assert_that(items, has_length(1))
			assert_that(items, has_key('tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'))
			
			item = items['tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273']
			assert_that(item, has_entry('Class', 'Hit'))
			assert_that(item, has_entry('Type', 'Highlight'))
			assert_that(item, has_entry('CollectionId', 'prealgebra'))
			assert_that(item, has_entry('TargetOID', 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'))
			assert_that(item, has_entry('NTIID', 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'))
			assert_that(item, has_entry('Snippet', 'multiply and DIVIDE In fact you may already'))
			assert_that(item, has_entry('ContainerId', 'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))

if __name__ == '__main__':
	unittest.main()
