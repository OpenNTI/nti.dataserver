#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
from StringIO import StringIO

from zope import interface

from zope.cachedescriptors.property import readproperty

from zope.proxy import ProxyBase

from nti.cabinet.interfaces import ISource

def get_file_size(source):
	result = None
	try:
		with open(source, "rb") as fp:
			result = os.fstat(fp.fileno()).st_size
	except AttributeError:
		pass
	return result

@interface.implementer(ISource)
class SourceFile(object):

	_data = None
	_v_fp = None

	def __init__(self, filename, data=None, contentType=None):
		self.filename = filename
		self.contentType = contentType
		if data is not None:
			self.data = data

	def _getData(self):
		return self._data
	def _setData(self, data):
		self._data = data
	data = property(_getData, _setData)

	@readproperty
	def mode(self):
		return "rb"

	def _get_v_fp(self):
		self._v_fp = StringIO(self.data) if self._v_fp is None else self._v_fp
		return self._v_fp

	def read(self, size=-1):
		return self._get_v_fp().read(size)

	def seek(self, offset, whence=0):
		return self._get_v_fp().seek(offset, whence)

	def tell(self):
		return self._get_v_fp().tell()

	def close(self):
		if self._v_fp is not None:
			self._v_fp.close()
		self._v_fp = None

	@property
	def length(self):
		result = str(self.data) if self.data is not None else u''
		return len(result)
	size = length

	def getSize(self):
		return self.length
	size = getSize

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.close()

@interface.implementer(ISource)
class DeferredSourceFile(SourceFile):

	def __init__(self, path, filename, data=None, contentType=None):
		super(DeferredSourceFile, self).__init__(filename, contentType=contentType)
		self.path = path
		if data is not None:
			self.data = data

	@property
	def _v_data_file(self):
		name = '.__%s__.dat' % self.filename
		return os.path.join(self.path, name)

	def _getData(self):
		with open(self._v_data_file, "rb") as fp:
			return fp.read()

	def _setData(self, data):
		# close resources
		self.close()
		# remove if set to None
		if data is None and os.path.exists(self._v_data_file):
			os.remove(self._v_data_file)
			return
		# write to deferred file
		with open(self._v_data_file, "wb") as fp:
			fp.write(data)

	data = property(_getData, _setData)

	def _get_v_fp(self):
		self._v_fp = open(self._v_data_file, "rb") if self._v_fp is None else self._v_fp
		return self._v_fp

	def remove(self):
		self.close()
		path = os.path.join(self.path, self.filename)
		if os.path.exists(path):
			os.remove(path)
		if os.path.exists(self._v_data_file):
			os.remove(self._v_data_file)

	@property
	def length(self):
		return get_file_size(self._v_data_file)
	size = length

	def getSize(self):
		return self.length
	size = getSize

@interface.implementer(ISource)
class SourceProxy(ProxyBase):

	length = property(lambda s: s.__dict__.get('_v_length'),
					  lambda s, v: s.__dict__.__setitem__('_v_length', v))

	contentType = property(
					lambda s: s.__dict__.get('_v_content_type'),
					lambda s, v: s.__dict__.__setitem__('_v_content_type', v))

	filename = property(
					lambda s: s.__dict__.get('_v_filename'),
					lambda s, v: s.__dict__.__setitem__('_v_filename', v))

	def __new__(cls, base, *args, **kwargs):
		return ProxyBase.__new__(cls, base)

	def __init__(self, base, filename=None, contentType=None, length=None):
		ProxyBase.__init__(self, base)
		self.length = length
		self.filename = filename
		self.contentType = contentType

	@readproperty
	def mode(self):
		return "rb"

	@property
	def size(self):
		return self.length

	def getSize(self):
		return self.size
