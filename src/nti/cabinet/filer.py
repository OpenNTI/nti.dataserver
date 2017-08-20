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
import shutil
import mimetypes
from datetime import datetime

from zope import interface

from nti.base._compat import text_

from nti.base.interfaces import DEFAULT_CONTENT_TYPE

from nti.cabinet.interfaces import ISource
from nti.cabinet.interfaces import ISourceFiler

from nti.cabinet.mixins import SourceBucket
from nti.cabinet.mixins import ReferenceSourceFile


def read_source(source):
    if hasattr(source, 'read'):
        result = source.read()
    elif hasattr(source, 'readContents'):
        result = source.readContents()
    elif hasattr(source, 'read_contents'):
        result = source.read_contents()
    elif hasattr(source, 'data'):
        result = source.data
    else:
        result = source
    return result


def transfer_to_storage_file(source, target):
    target.data = read_source(source)
    if getattr(source, 'contentType', None):
        target.contentType = source.contentType


def transfer_to_native_file(source, target):
    with open(target, "wb") as fp:
        data = read_source(source)
        if data is not None:
            fp.write(data)


@interface.implementer(ISourceFiler)
class DirectoryFiler(object):

    default_bucket = None

    def __init__(self, path):
        self.path = self.prepare(path) if path else None

    def prepare(self, path):
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            os.makedirs(path)
        elif not os.path.isdir(path):
            raise IOError("%s is not directory", path)
        return path

    def reset(self, path=None):
        path = self.path if not path else path
        if path:
            path = os.path.expanduser(path)
            shutil.rmtree(path, True)
            return True
        return False

    def _get_unique_file_name(self, path, key, now=None):
        counter = 0
        now = now or time.time()  # current time
        key_noe, ext = os.path.splitext(key)
        now = datetime.fromtimestamp(now).strftime("%H.%M.%S")
        while True:
            counter += 1
            hex_key = u"%s.%s" % (now, counter)
            newtext = u"%s.%s%s" % (key_noe, hex_key, ext)
            newtext = os.path.join(path, newtext)
            if not os.path.exists(newtext):
                break
        return newtext

    def save(self, key, source, contentType=None, bucket=None, overwrite=False,
             relative=True, **unused_kwargs):
        contentType = contentType or DEFAULT_CONTENT_TYPE
        key = os.path.split(key)[1]  # proper name

        bucket = bucket or self.default_bucket

        # get output directory
        out_dir = os.path.join(self.path, bucket) if bucket else self.path
        out_dir = os.path.normpath(out_dir)
        if not out_dir.startswith(self.path):
            raise IOError("Invalid bucket name")

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if not overwrite:
            out_file = self._get_unique_file_name(out_dir, key)
        else:
            out_file = os.path.join(out_dir, key)

        transfer_to_native_file(source, out_file)
        if relative:
            out_file = os.path.relpath(out_file, self.path)
        return out_file

    def get(self, key, bucket=None):
        bucket = bucket or self.default_bucket
        if bucket:
            if not bucket.startswith(self.path):
                bucket = os.path.join(self.path, bucket)
                bucket = os.path.normpath(bucket)
            key = os.path.join(bucket, key)
        elif not key.startswith(self.path):
            key = os.path.join(self.path, key)
            key = os.path.normpath(key)
        if not key.startswith(self.path) or not os.path.exists(key):
            return None

        # compute a parent
        bucket = os.path.split(key)[0] + os.path.sep + '..'
        bucket = os.path.normpath(bucket)
        if not bucket.startswith(self.path):
            bucket = None
        else:
            bucket = os.path.relpath(bucket, self.path)
        parent = SourceBucket(bucket, self)

        if os.path.isdir(key):
            bucket = os.path.relpath(key, self.path)
            result = SourceBucket(bucket, self)
        else:
            key_path, name = os.path.split(key)
            contentType = mimetypes.guess_type(name.lower())[0]
            result = ReferenceSourceFile(name=name,
                                         path=key_path,
                                         contentType=text_(contentType))
        result.__parent__ = parent
        return result

    def remove(self, key, bucket=None):
        result = self.get(key, bucket=bucket)
        if result is not None:
            if hasattr(result, 'remove'):
                result.remove()
            else:
                if not key.startswith(self.path):
                    key = os.path.join(self.path, key)
                if os.path.isdir(key):
                    shutil.rmtree(key, True)
                else:
                    os.remove(key)
            return True
        return False

    def contains(self, key, bucket=None):
        bucket = bucket or self.default_bucket
        if bucket:
            if not bucket.startswith(self.path):
                bucket = os.path.join(self.path, bucket)
                bucket = os.path.normpath(bucket)
            key = os.path.join(bucket, key)
        elif not key.startswith(self.path):
            key = os.path.join(self.path, key)
            key = os.path.normpath(key)
        result = key.startswith(self.path) and os.path.exists(key)
        return result

    def list(self, bucket=None):
        bucket = bucket or self.default_bucket
        path = os.path.join(self.path, bucket) if bucket else self.path
        path = os.path.normpath(path)
        if not path.startswith(self.path) or not os.path.isdir(path):
            raise IOError("Invalid bucket name")
        result = []
        for name in os.listdir(path):
            name = os.path.join(bucket, name) if bucket else name
            result.append(name)
        return result

    def is_bucket(self, key):
        if not key.startswith(self.path):
            key = os.path.join(self.path, key)
        key = os.path.normpath(key)
        if not key.startswith(self.path) or not os.path.exists(key):
            return False
        return os.path.isdir(key)
    isBucket = is_bucket

    def key_name(self, identifier):
        return os.path.split(identifier)[1]
    keyName = key_name

    def get_external_link(self, item):
        return item.filename if ISource.providedBy(item) else None
    to_external_link = get_external_link
