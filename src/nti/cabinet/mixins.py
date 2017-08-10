#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import time
from io import BytesIO

from zope import interface

from zope.cachedescriptors.property import readproperty
from zope.cachedescriptors.property import CachedProperty

from zope.proxy import ProxyBase

from nti.base.interfaces import DEFAULT_CONTENT_TYPE

from nti.base.interfaces import ILastModified

from nti.cabinet.interfaces import ISource
from nti.cabinet.interfaces import ISourceBucket

from nti.property.property import alias

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

# Buckets


@EqHash('__name__')
@interface.implementer(ISourceBucket)
class SourceBucket(object):

    __name__ = None
    __parent__ = None

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


@interface.implementer(ISource, ILastModified)
class SourceProxy(ProxyBase):
    """
    Source proxy for a io.file object
    """

    __parent__ = property(
        lambda s: s.__dict__.get('_v__parent__'),
        lambda s, v: s.__dict__.__setitem__('_v__parent__', v))

    length = property(
        lambda s: s.__dict__.get('_v_length'),
        lambda s, v: s.__dict__.__setitem__('_v_length', v))

    contentType = property(
        lambda s: s.__dict__.get('_v_content_type'),
        lambda s, v: s.__dict__.__setitem__('_v_content_type', v))

    filename = property(
        lambda s: s.__dict__.get('_v_filename'),
        lambda s, v: s.__dict__.__setitem__('_v_filename', v))

    createdTime = property(
        lambda s: s.__dict__.get('_v_createdTime'),
        lambda s, v: s.__dict__.__setitem__('_v_createdTime', v))

    lastModified = property(
        lambda s: s.__dict__.get('_v_lastModified'),
        lambda s, v: s.__dict__.__setitem__('_v_lastModified', v))

    def __new__(cls, base, *unused_args, **unused_kwargs):
        return ProxyBase.__new__(cls, base)

    def __init__(self, base, filename=None, contentType=None, length=None,
                 createdTime=0, lastModified=0):
        ProxyBase.__init__(self, base)
        self.length = length
        self.filename = filename
        self.createdTime = createdTime or 0
        self.lastModified = lastModified or 0
        self.contentType = contentType or DEFAULT_CONTENT_TYPE

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

    @property
    def data(self):
        return self.read()


@EqHash('filename')
@interface.implementer(ISource, ILastModified)
class SourceFile(SchemaConfigured):
    createDirectFieldProperties(ISource)

    __parent__ = None

    _data = None
    _time = None

    def __init__(self, *args, **kwargs):
        data = kwargs.pop('data', None)
        self.name = kwargs.pop('name', None)
        self.path  = kwargs.pop('path', None) or u''
        contentType = kwargs.pop('contentType', None)
        createdTime = kwargs.pop('createdTime', None)
        lastModified = kwargs.pop('lastModified', None)
        SchemaConfigured.__init__(self, *args, **kwargs)
        self.reset(contentType, data, createdTime, lastModified)

    def reset(self, contentType, data, createdTime, lastModified):
        self._time = time.time()
        self.contentType = contentType or DEFAULT_CONTENT_TYPE
        if data is not None:
            self.data = data
        if createdTime is not None:
            self.createdTime = createdTime
        if lastModified is not None:
            self.lastModified = lastModified

    @property
    def filename(self):
        return os.path.join(self.path, self.name)

    def _getData(self):
        return self._data

    def _setData(self, data):
        self._data = data
    data = property(_getData, _setData)

    @readproperty
    def mode(self):
        return "rb"

    @readproperty
    def createdTime(self):
        return self._time

    @readproperty
    def lastModified(self):
        return self._time

    @CachedProperty('data')
    def _v_fp(self):
        return BytesIO(self.data)

    def read(self, size=-1):
        return self._v_fp.read(size) if size != -1 else self.data

    def seek(self, offset, whence=0):
        return self._v_fp.seek(offset, whence)

    def tell(self):
        return self._v_fp.tell()

    def close(self):
        pass

    @property
    def length(self):
        result = self.data if self.data is not None else u''
        return len(result)
    size = length

    def getSize(self):
        return self.length
    size = getSize

    def readContents(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *unused_args):
        self.close()

    @property
    def __name__(self):
        return self.name
NamedSource = SourceFile


@interface.implementer(ISource)
class ReferenceSourceFile(SourceFile):

    def _getData(self):
        with open(self.filename, "rb") as fp:
            return fp.read()

    def _setData(self, data):
        # close resources
        self.close()
        if data is None and os.path.exists(self.filename):
            data = b''  # 0 byte file
        # write to file
        with open(self.filename, "wb") as fp:
            fp.write(data)
    data = property(_getData, _setData)

    @readproperty
    def _v_fp(self):
        self._v_fp = open(self.filename, "rb")
        return self._v_fp

    def close(self):
        if '_v_fp' in self.__dict__:
            self._v_fp.close()
            delattr(self, '_v_fp')

    def remove(self):
        self.close()
        if os.path.exists(self.filename):
            os.remove(self.filename)

    @property
    def length(self):
        return get_file_size(self.filename)
    size = length

    def getSize(self):
        return self.length
    size = getSize

    @readproperty
    def createdTime(self):
        return get_file_createdTime(self.filename) or 0

    @readproperty
    def lastModified(self):
        return get_file_lastModified(self.filename) or 0
