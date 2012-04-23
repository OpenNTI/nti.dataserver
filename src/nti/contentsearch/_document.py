# Copyright (c) 2008 Agendaless Consulting and Contributors.
# (http://www.agendaless.com), All Rights Reserved
# Disclaimer
#	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND
#	ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
#	TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
#	PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#	HOLDERS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#	EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
#	TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#	DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#	ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
#	TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
#	THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
#	SUCH DAMAGE.

import random

from persistent import Persistent
from BTrees.IOBTree import IOBTree
from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree

import BTrees

_marker = ()

class DocumentMap(Persistent):

	_v_nextid = None
	family = BTrees.family32
	_randrange = random.randrange
	docid_to_metadata = None # latch for b/c

	def __init__(self):
		self.docid_to_address = IOBTree()
		self.address_to_docid = OIBTree()
		self.docid_to_metadata = IOBTree()

	def docid_for_address(self, address):
		return self.address_to_docid.get(address)

	def address_for_docid(self, docid):
		return self.docid_to_address.get(docid)

	def add(self, address, docid=_marker):
		if docid is _marker or docid is None:
			docid = self.new_docid()
		
		self.docid_to_address[docid] = address
		self.address_to_docid[address] = docid
	
		return docid

	def remove_docid(self, docid):
		self._check_metadata()
		
		address = self.docid_to_address.get(docid, _marker)
		if address is _marker:
			return False
		old_docid = self.address_to_docid.get(address, _marker)
		if (old_docid is not _marker) and (old_docid != docid):
			self.remove_docid(old_docid)
		
		if docid in self.docid_to_address:
			del self.docid_to_address[docid]
		if address in self.address_to_docid:
			del self.address_to_docid[address]
		if docid in self.docid_to_metadata:
			del self.docid_to_metadata[docid]
			
		return True
	
	def remove_address(self, address):        
		self._check_metadata()

		docid = self.address_to_docid.get(address, _marker)
		if docid is _marker:
			return False
		
		old_address = self.docid_to_address.get(docid, _marker)
		if (old_address is not _marker) and (old_address != address):
			self.remove_address(old_address)

		if docid in self.docid_to_address:
			del self.docid_to_address[docid]
		if address in self.address_to_docid:
			del self.address_to_docid[address]
		if docid in self.docid_to_metadata:
			del self.docid_to_metadata[docid]

		return True

	def _check_metadata(self):
		# backwards compatibility
		if self.docid_to_metadata is None:
			self.docid_to_metadata = IOBTree()

	def add_metadata(self, docid, data):
		if not docid in self.docid_to_address:
			raise KeyError(docid)
		if len(data.keys()) == 0:
			return
		self._check_metadata()
		meta = self.docid_to_metadata.setdefault(docid, OOBTree())
		for k in data:
			meta[k] = data[k]

	def remove_metadata(self, docid, *keys):
		self._check_metadata()
		if keys:
			meta = self.docid_to_metadata.get(docid, _marker)
			if meta is _marker:
				raise KeyError(docid)
			for k in keys:
				if k in meta:
					del meta[k]
			if not meta:
				del self.docid_to_metadata[docid]
		else:
			if not (docid in self.docid_to_metadata):
				raise KeyError(docid)
			del self.docid_to_metadata[docid]

	def get_metadata(self, docid):
		if self.docid_to_metadata is None:
			raise KeyError(docid)
		meta = self.docid_to_metadata[docid]
		return meta

	def _reverse(self, x):
		idx = 3 if x < 0 else 2
		x = int(bin(x)[idx:].zfill(31)[::-1], 2)
		if idx == 2:
			return min(x, self.family.maxint)
		else:
			return max(x, self.family.minint)
	
	def new_docid(self):
		while True:
			if self._v_nextid is None:
				self._v_nextid = self._randrange(self.family.minint, self.family.maxint)
			uid = self._reverse(self._v_nextid)
			self._v_nextid += 1
			if uid not in self.docid_to_address:
				return uid
			self._v_nextid = None
			