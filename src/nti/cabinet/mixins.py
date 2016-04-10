#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO

from zope import interface

from zope.cachedescriptors.property import readproperty

from zope.container.contained import Contained

from zope.proxy import ProxyBase

from nti.cabinet.interfaces import ISource
from nti.cabinet.interfaces import ISourceBucket

from nti.common.property import alias

from nti.schema.schema import EqHash

# Buckets

@EqHash('__name__')
@interface.implementer(ISourceBucket)
class SourceBucket(Contained):
	
	name = alias('__name__')

	def __init__(self, bucket, filer):
		self.filer = filer
		self.__name__ = bucket

	@property
	def bucket(self):
		return self.__name__

	@property
	def name(self):
		return os.path.split(self.__name__)[1] if self.__name__ else u''
	
	def getChildNamed(self, name):
		if not name.startswith(self.bucket):
			name = os.path.join(self.bucket, name)
		result = self.filer.get(name)
		return result
	
	def enumerateChildren(self):
		return self.filer.list(self.bucket)

# Key Sources

def _get_file_stat(source, name):
	result = None
	try:
		with open(source, "rb") as fp:
			result = getattr(os.fstat(fp.fileno()), name)
	except Exception:
		pass
	return result

def get_file_size(source):
	return _get_file_stat(source, 'st_size')

def get_file_createdTime(source):
	return _get_file_stat(source, 'st_ctime')

def get_file_lastModified(source):
	return _get_file_stat(source, 'st_mtime')

@interface.implementer(ISource)
class SourceProxy(ProxyBase):
	"""
	Source proxy for a io.file object
	"""
	__parent__ = property(lambda s: s.__dict__.get('_v__parent__'),
					 	  lambda s, v: s.__dict__.__setitem__('_v__parent__', v))
		
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
		self.contentType = contentType or u'application/octet-stream'

	@readproperty
	def mode(self):
		return "rb"

	@property
	def size(self):
		return self.length

	def getSize(self):
		return self.size
	
	@property
	def __name__(self):
		return self.filename
	name = __name__

	def readContents(self):
		return self.read()

@interface.implementer(ISource)
class SourceFile(object):

	_data = None
	_v_fp = None
	__parent__ = None

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
		return self._get_v_fp().read(size) if size != -1 else self.data

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

	def readContents(self):
		return self.data

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.close()

	@property
	def __name__(self):
		return self.filename
	name = __name__

@interface.implementer(ISource)
class ReferenceSourceFile(SourceFile):

	def __init__(self, path, filename, data=None, contentType=None):
		super(ReferenceSourceFile, self).__init__(filename, contentType=contentType)
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