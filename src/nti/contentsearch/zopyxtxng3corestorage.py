# -*- coding: utf-8 -*-
"""
Zopyx override for index storage.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import BTrees.Length 

from BTrees.IIBTree import IISet as IISet32
from BTrees.IIBTree import IIBTree as IIBTree32
from BTrees.IIBTree import difference as difference32

from BTrees.LOBTree import LOBTree
from BTrees.LLBTree import LLBTree
from BTrees.LLBTree import union as union64

from zope import interface
from zope.component.interfaces import IFactory

from zopyx.txng3.core import widcode as zopyx_widcode
from zopyx.txng3.core import storage as zopyx_storage
from zopyx.txng3.core.interfaces import IStorageWithTermFrequency
	
from .zopyxtxng3coredoclist import DocidList

class Storage(zopyx_storage.Storage):
	
	def clear(self):
		self._doc2wid = LOBTree()   # docid -> [wordids]
		self._wid2doc = LOBTree()   # wordid -> [docids]
		self._docweight = LLBTree() # docid -> (# terms in document)
		self._length = BTrees.Length.Length()
	
	def insertDocument(self, docid, widlist):
	
		if not self._doc2wid.has_key(docid):
			self._length.change(1)
	
		enc_widlist = zopyx_widcode.encode(widlist)
		old_enc_widlist = self._doc2wid.get(docid)
		if old_enc_widlist is not None:
			old_enc_widlist = old_enc_widlist.get() # unwrap _PS instance
	
		removed_wordids = []
		if old_enc_widlist != enc_widlist :
			self._doc2wid[docid] = zopyx_storage._PS(enc_widlist)
			if old_enc_widlist is not None:
				old_widlist = IISet32(zopyx_widcode.decode(old_enc_widlist))
				removed_wordids = difference32(old_widlist, IISet32(widlist))
	
		tree = self._wid2doc
		tree_has = tree.has_key
		count = 0
		for wid in widlist:
			count += 1
			if not tree_has(wid):
				tree[wid] = DocidList([docid])
			else:
				if not docid in tree[wid]:   
					tree[wid].insert(docid)
	
		for wid in removed_wordids:
			if tree_has(wid):
				try:
					tree[wid].remove(docid)
				except KeyError:
					pass
	
		self._docweight[docid] = count
	
	def getDocumentsForWordId(self, wordid):
		try:
			return self._wid2doc[wordid]
		except (TypeError, KeyError):
			return DocidList()
	
	def getDocumentsForWordIds(self, wordidlist):
		r = DocidList()
		for wordid in wordidlist:
			try:
				docids = self._wid2doc[wordid]
			except (TypeError, KeyError):
				continue
			
			r = union64(r, docids)
		return r
	
	def hasContigousWordids(self, docid, wordids):
		# sometimes there are null word ids. This occurs
		# where it the word cannot be found in the lexicon
		for w in wordids:
			if w is None:
				return False
		return super(Storage, self).hasContigousWordids(docid, wordids)

@interface.implementer(IStorageWithTermFrequency)
class StorageWithTermFrequency(Storage):

	def clear(self):
		Storage.clear(self)
		self._frequencies = LOBTree()   # docid -> (wordid -> #occurences)
	
	def insertDocument(self, docid, widlist):
		Storage.insertDocument(self, docid, widlist)
		
		occurences = {}   # wid -> #(occurences)
		# num_wids = float(len(widlist))
		for wid in widlist:
			if not occurences.has_key(wid):
				occurences[wid] = 1
			else:
				occurences[wid] += 1
		
		self._frequencies[docid] = IIBTree32()
		tree = self._frequencies[docid]
		for wid,num in occurences.items():
			tree[wid] = num

	def removeDocument(self, docid):
		# note that removing a non existing document should not
		# raise an exception
		Storage.removeDocument(self, docid)
		try:
			del self._frequencies[docid]
		except KeyError:
			pass

	def getTermFrequency(self):
		return self._frequencies

@interface.implementer(IFactory)
class _StorageFactory(object):
	
	def __init__(self, klass):
		self._klass = klass
	
	def __call__(self):
		return self._klass()
	
	def getInterfaces(self):
		return interface.implementedBy(self._klass)

StorageFactory = _StorageFactory(Storage)
StorageWithTermFrequencyFactory = _StorageFactory(StorageWithTermFrequency)
