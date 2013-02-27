# -*- coding: utf-8 -*-
"""
"File-like objects that read from or write to a series of equal size blocks

Based on https://bitbucket.org/pypy/pypy/src/py3k/lib-python/2.7/StringIO.py?at=py3k

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from errno import EINVAL

from persistent import Persistent
from persistent.list import PersistentList

from nti.utils.property import alias

class Block(object):
	
	size = 1024
	
	def __init__(self, size=None):
		self.len = 0
		if size and size != self.size: 
			self.size = size
		self.data = bytearray(b'\0'*self.size)
	
	@property
	def available(self):
		return self.size - self.len
	
	def read(self, p=0, n=-1):
		if n is None or n < 0:
			_end = self.len
		else:
			_end = min(p + n, self.len)
		result = self.data[p:_end]
		return result
	
	def truncate(self, offset):
		self.len = offset
		self.data[offset:self.size] = b'\0'*(self.size-offset)
		
	def write(self, s, pos=None):
		l = len(s)
		pos = self.len if pos is None else pos
		result = max(0, self.size - pos)
		if result > 0:
			if l < result:
				result = l
				self.data[pos:pos+l] = s
				if pos+l > self.len:
					self.len = pos+l
			else:
				self.data[pos:self.size] = s[:result]
				self.len = self.size
			
		return result
			
	def __len__(self):
		return self.len
	
	def __str__(self):
		return "%s" % self.len
	
	def __repr(self):
		return "%s<%r>" % (self.__class__.name, self.data[:self.len])

class BlockIO(object):

	block_size = 1024
	block_factory = Block
	block_list_factory = list
		
	def __init__(self, block_size=None):
		self.len = 0
		self._v_pos = 0
		self.block_list = self.block_list_factory()
		if block_size: self.block_size = block_size

	pos = alias("_v_pos")
	
	def __len__(self):
		return len(self.block_list)
	
	def __setstate__(self, d):
		super(BlockIO, self).__setstate__(d)
		self._v_pos = 0
	
	def __iter__(self):
		return self
	
	def __str__(self):
		return "%s,%s,%s" % (len(self), self.pos, self.len)
	
	__repr__ = __str__

	@property
	def current_block(self):
		return self.block_list[self.current_block_idx]
	
	@property
	def current_block_idx(self):
		return self.pos / self.block_size
	
	@property
	def current_block_offset(self):
		return self.pos - (self.current_block_idx  * self.block_size)
	
	def next(self):
		r = self.readline()
		if not r:
			raise StopIteration
		return r

	def close(self):
		pass

	def isatty(self):
		return False

	def seek(self, pos, mode = 0):
		"""Set the file's current position.

		The mode argument is optional and defaults to 0 (absolute file
		positioning); other values are 1 (seek relative to the current
		position) and 2 (seek relative to the file's end).

		"""
		if mode == 1:
			pos += self.pos
		elif mode == 2:
			pos += self.len
		self.pos = max(0, pos)

	def tell(self):
		return self.pos

	def read(self, n=-1):
		"""Read at most size bytes from the file
		(less if the read hits EOF before obtaining size bytes).

		If the size argument is negative or omitted, read all data until EOF
		is reached. The bytes are returned as a string object. An empty
		string is returned when EOF is encountered immediately.
		"""
		if n is None or n < 0:
			newpos = self.len
		else:
			newpos = min(self.pos+n, self.len)
		
		result = bytearray()
		while self.pos < newpos:
			max_bytes = newpos - self.pos
			b = self.current_block
			offset = self.current_block_offset
			r = b.read(offset, max_bytes)
			self.pos += len(r)
			result.extend(r)

		return result

	def readline(self, length=None):
		"""Read one entire line from the file.

		A trailing newline character is kept in the string (but may be absent
		when a file ends with an incomplete line). If the size argument is
		present and non-negative, it is a maximum byte count (including the
		trailing newline) and an incomplete line may be returned.

		An empty string is returned only when EOF is encountered immediately.
		"""
		spos = self.pos
		result = bytearray()
		while self.pos < self.len:
			b = self.current_block
			offset = self.current_block_offset
			
			# read all
			r = b.read(offset)
			
			# find newline character

			i = r.find(b'\n')
			do_exit = i >= 0
			r = r[:i+1] if do_exit else r
			
			# add to buffer
			result.extend(r)
			
			# check max byte count
			if length is not None and length > 0:
				if len(result) >= length:
					result = result[:length]
					self.pos = min(spos + length, self.len)
					do_exit = True
			else:	
				self.pos += len(r)
				
			if do_exit:
				break

		return result

	def readlines(self, sizehint = 0):
		"""Read until EOF using readline() and return a list containing the
		lines thus read.

		If the optional sizehint argument is present, instead of reading up
		to EOF, whole lines totalling approximately sizehint bytes (or more
		to accommodate a final whole line).
		"""
		total = 0
		lines = []
		line = self.readline()
		while line:
			lines.append(line)
			total += len(line)
			if 0 < sizehint <= total:
				break
			line = self.readline()
		return lines

	def truncate(self, size=None):
		"""Truncate the file's size.

		If the optional size argument is present, the file is truncated to
		(at most) that size. The size defaults to the current position.
		The current file position is not changed unless the position
		is beyond the new file size.

		If the specified size exceeds the file's current size, the
		file remains unchanged.
		"""
		if size is None:
			size = self.pos
		elif size < 0:
			raise IOError(EINVAL, "Negative size not allowed")
		elif size < self.pos:
			self.pos = size
		elif size >= self.len:
			return
		
		if size == 0:
			blocks_to_remove = len(self.block_list)
		else:
			blocks_to_remove = len(self.block_list) - 1 - self.current_block_idx
			
		for _ in xrange(blocks_to_remove):
			self.block_list.pop()
			
		if self.block_list:
			offset = self.current_block_offset
			self.current_block.truncate(offset)
		
		self.len = size

	def _allocate(self, max_bytes):
		blocks = (max_bytes / self.block_size) + 1
		for _ in xrange(blocks):
			self.block_list.append(self.block_factory(self.block_size))
		
	def write(self, s):
		if not s: return
		
		ls = len(s)
		spos = self.pos
		slen = self.len
		if spos > slen: # grow the file
			lboundary = len(self.block_list) * self.block_size
			if spos > lboundary:
				self._allocate(spos-slen)
			slen = spos
			
		if spos+ls > slen:
			if not self.block_list: # no blocks
				self._allocate(ls)
			else:
				bidx = slen / self.block_size
				rboundary = (bidx+1) * self.block_size
				if spos+ls >= rboundary:
					self._allocate(spos+ls-rboundary)
			slen = spos+ls
			
		result = 0
		offset = self.current_block_offset
		while result < ls:
			b = self.current_block
			w = b.write(s[result:], offset)
			offset = 0
			result += w
			self.pos += w
				
		self.len = slen
		return result

	def writelines(self, iterable):
		"""Write a sequence of strings to the file. The sequence can be any
		iterable object producing strings, typically a list of strings. There
		is no return value.

		(The name is intended to match readlines(); writelines() does not add
		line separators.)
		"""
		write = self.write
		for line in iterable:
			write(line)

	def flush(self):
		pass

	def getvalue(self):
		"""
		Retrieve the entire contents of the "file"
		"""
		result = bytearray()
		for b in self.block_list:
			result.extend(b.read())
		return result

class PesistentBlock(Persistent, Block):
	pass

class PesistentBlockIO(Persistent, BlockIO):
	block_factory = PesistentBlock
	block_list_factory = PersistentList

