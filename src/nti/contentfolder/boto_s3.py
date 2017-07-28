#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

import boto.s3.key

from zope.cachedescriptors.property import readproperty

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import INamedContainer


def get_key(context):
    path = []
    result = ''
    current = context
    while current is not None:
        if IRootFolder.providedBy(current):
            break
        try:
            path.append(current.__name__)
            current = current.__parent__
        except AttributeError:
            break
    if path:
        path.reverse()
        result = '/'.join(path)
        if INamedContainer.providedBy(context):
            result += '/'
    return result


def is_boto_available(environ=None):
    environ = os.environ if environ is None else environ
    return bool(    environ.get('AWS_BUCKET_NAME')
                and environ.get('AWS_ACCESS_KEY_ID')
                and environ.get('AWS_SECRET_ACCESS_KEY'))


class BotoS3Mixin(object):

    grant = 'public-read-write'

    @readproperty
    def settings(self):
        return os.environ

    @readproperty
    def aws_access_key_id(self):
        return self.settings.get('AWS_ACCESS_KEY_ID')

    @readproperty
    def aws_secret_access_key(self):
        return self.settings.get('AWS_SECRET_ACCESS_KEY')

    @readproperty
    def bucket_name(self):
        return self.settings.get('AWS_BUCKET_NAME')

    def _connection(self, debug=False):
        connection = boto.connect_s3(aws_access_key_id=self.aws_access_key_id,
                                     aws_secret_access_key=self.aws_secret_access_key)
        connection.debug = debug
        return connection

    def get_all_keys(self, debug=False):
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            return [x.key for x in bucket.list()]
        finally:
            connection.close()

    def get_key(self, context):
        return get_key(context)

    def exists_key(self, key, debug=False):
        """
        Check if key exists
        """
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = boto.s3.key.Key(bucket, key)
            return k.exists()
        except Exception as e:
            logger.error(
                "Error while checking existence of key %s. %s", key, e)
            return False
        finally:
            connection.close()

    def contents_key(self, key, encoding=None, debug=False):
        """
        Get the contents of key
        """
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = boto.s3.key.Key(bucket, key)
            return k.get_contents_as_string(encoding=encoding)
        finally:
            connection.close()

    def size_key(self, key, debug=False):
        """
        Get the content size of key
        """
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = bucket.lookup(key)
            return k.size
        finally:
            connection.close()

    def save_key(self, key, data='', debug=False):
        """
        Create file or Folder.
        """
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = boto.s3.key.Key(bucket, key)
            k.set_contents_from_string(data, policy=self.grant)
        finally:
            connection.close()

    def remove_key(self, key, debug=False):
        """
        Delete file or Folder, key ends with '/' represents folder.
        """
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            if key.endswith('/'):
                keys = [x.key for x in bucket.list(prefix=key)]
                bucket.delete_keys(keys)
            bucket.delete_key(key)
        finally:
            connection.close()
        return True

    def rename_key(self, oldKey, newKey, debug=False):
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = bucket.lookup(oldKey)
            if k:
                if oldKey.endswith('/'):
                    for k in bucket.list(prefix=oldKey):
                        n = newKey + k.key[len(oldKey):]
                        k.copy(self.bucket_name, n, preserve_acl=True)
                        k.delete()
                else:
                    k.copy(self.bucket_name, newKey, preserve_acl=True)
                    k.delete()
        finally:
            connection.close()

    def move_key(self, srcKey, targetKey, debug=False):
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = bucket.lookup(srcKey)
            if k:
                if srcKey.endswith('/'):
                    for k in bucket.list(prefix=srcKey):
                        n = targetKey + k.key[len(srcKey):]
                        bucket.delete_key(n)
                        k.copy(self.bucket_name, n, preserve_acl=True)
                        k.delete()
                else:
                    bucket.delete_key(targetKey)
                    k.copy(self.bucket_name, targetKey, preserve_acl=True)
                    k.delete()
        finally:
            connection.close()

    def clear_keys(self, parentKey, debug=False):
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            keys = [
                x.key for x in bucket.list(prefix=parentKey) if x.key != parentKey
            ]
            bucket.delete_keys(keys)
        finally:
            connection.close()

    def to_external_s3_href(self, obj=None, key=None, debug=False):
        key = self.get_key(obj) if obj is not None else key
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name, validate=False)
            k = boto.s3.key.Key(bucket, key)
            return k.generate_url(expires_in=0, query_auth=False)
        finally:
            connection.close()
