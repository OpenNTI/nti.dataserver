import struct, os, cPickle
import xml.sax
import sys
import zlib
import gzip

def main(args):
	action = args.pop(0)

	if action == 'generate':
		createDictionary(args.pop(0), args.pop(0))

	if action == 'lookup':
		print lookup(args.pop(0), args.pop(0))

def createDictionary(wikidumpname, destname):


	#Keep an index of word to location in the file
	index={}

	dictionary=gzip.open(destname, 'wb')

	parser=xml.sax.make_parser()
	parser.setContentHandler(WiktionaryDumpHandler(index, dictionary))
	dump=open(wikidumpname)
	parser.parse(dump)
	dump.close()

	dictionary.close()

	path, ext=os.path.splitext(destname)

	indexLocation=path+'.index'

	indexFile=gzip.open(indexLocation, 'wb')

	cPickle.dump(index, indexFile)

	indexFile.close()

import time

def lookup(dicname, term):
	start = time.time()
	indexFile=gzip.open(dicname+'.index','rb')
	index=cPickle.load(indexFile)
	indexFile.close()

	end=time.time()

	print 'Took %s seconds to load the index' % (end-start)

	start=time.time()
	if term not in index:
		return 'Not found'

	print 'Checking at location %s'%index[term]

	dictionary=gzip.open(dicname+'.bin', 'rb')
	dictionary.seek(index[term])

	res= cPickle.load(dictionary)
	dictionary.close()
	end=time.time()

	print 'Took %s seconds to lookup the entry' % (end-start)
	return res

from xml.sax.handler import ContentHandler

from pywikipedia.wiktionary.wiktionarypage import *

class WiktionaryDumpHandler(ContentHandler):

	def __init__(self,index, dictionary):
		self.index=index
		self.dictionary=dictionary

		self.name=u''
		self.nameLabel='title'
		self.insideName=False

		self.markup=u''
		self.markupLabel='text'
		self.insideMarkup=False

		self.pageLabel='page'
		self.insidePage=False

		self.page=0

	def startElement(self, localname, attrs):
		if localname == self.pageLabel:
			self.insidePage=True
			self.page=self.page+1
			print 'Found page %d'%self.page
		elif localname == self.nameLabel:
			self.insideName=True
			self.name=''
		elif localname == self.markupLabel:
			self.insideMarkup=True
			self.markup=''

	def endElement(self, localname):
		if localname == self.pageLabel:
			self.insidePage=False
		elif localname == self.nameLabel:
			self.insideName=False
			#In the event that its not a word (based on the title) set that we are out of the page so we don't collect wikimarkup
			if self.name.find(':')>-1:
				self.name=''
				self.insidePage=False
		elif self.insidePage and localname == self.markupLabel:
			self.insideMarkup=False
			self.persistEntry(self.name, self.markup)

	def persistEntry(self,title, text):
		if text.lower().find('==english==') < 0:
			return
		loc=self.dictionary.tell()
		#cPickle.dump(text, self.dictionary)
		page=WiktionaryPage('en', title)
		page.parseWikiPage(text)
		cPickle.dump(page, self.dictionary)
		self.index[title]=loc

	def characters(self, data):
		if self.insidePage and self.insideName:
			self.name=self.name+data
		elif self.insidePage and self.insideMarkup:
			self.markup=self.markup+data




if __name__ == '__main__':
	main(sys.argv[1:])
