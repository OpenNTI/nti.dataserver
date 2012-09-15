from __future__ import print_function, unicode_literals

###########################################################################
# TextIndexNG V 3                
# The next generation TextIndex for Zope
#
# This software is governed by a license. See
# LICENSE.txt for the terms of this license.
###########################################################################

"""
Storage of docid -> wordids mapping

$Id: storage.py 2194 2009-12-08 06:06:24Z ajung $
"""

import BTrees.Length 

from BTrees.IIBTree import IIBTree, IISet
from BTrees.IIBTree import difference as difference32

from BTrees.LOBTree import LOBTree
from BTrees.LLBTree import union as union64
from BTrees.LLBTree import LLBTree

from zope.component.interfaces import IFactory
from zope.interface import implements, implementedBy

from zopyx.txng3.core import widcode as zopywidcode
from zopyx.txng3.core import storage as zopystorage
from zopyx.txng3.core.interfaces import IStorageWithTermFrequency

from nti.contentsearch.zopyxtxng3coredoclist import DocidList

class Storage(zopystorage.Storage):
	
	def clear(self):
		self._doc2wid = LOBTree()   # docid -> [wordids]
		self._wid2doc = LOBTree()   # wordid -> [docids]
		self._docweight = LLBTree() # docid -> (# terms in document)
		self._length = BTrees.Length.Length()
	
	def insertDocument(self, docid, widlist):
	
		if not self._doc2wid.has_key(docid):
			self._length.change(1)
	
		enc_widlist = zopywidcode.encode(widlist)
		old_enc_widlist = self._doc2wid.get(docid)
		if old_enc_widlist is not None:
			old_enc_widlist = old_enc_widlist.get() # unwrap _PS instance
	
		removed_wordids = []
		if old_enc_widlist != enc_widlist :
			self._doc2wid[docid] = zopystorage._PS(enc_widlist)
			if old_enc_widlist is not None:
				old_widlist = IISet(zopywidcode.decode(old_enc_widlist))
				removed_wordids = difference32(old_widlist, IISet(widlist))
	
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

class StorageWithTermFrequency(Storage):
	implements(IStorageWithTermFrequency)

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
		
		self._frequencies[docid] = IIBTree()
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

class _StorageFactory:
	implements(IFactory)
	
	def __init__(self, klass):
		self._klass = klass
	
	def __call__(self):
		return self._klass()
	
	def getInterfaces(self):
		return implementedBy(self._klass)

StorageFactory = _StorageFactory(Storage)
StorageWithTermFrequencyFactory = _StorageFactory(StorageWithTermFrequency)
