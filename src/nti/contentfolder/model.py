#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import six

import boto

from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import readproperty
from zope.cachedescriptors.property import CachedProperty

from zope.location.location import locate

from zope.mimetype.interfaces import IContentTypeAware

from zope.security.management import system_user

from ZODB.interfaces import IConnection

from nti.base.interfaces import IFile

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import IS3RootFolder
from nti.contentfolder.interfaces import IContentFolder
from nti.contentfolder.interfaces import INamedContainer
from nti.contentfolder.interfaces import IS3ContentFolder

from nti.contentfolder.utils import compute_path

from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin

from nti.namedfile.file import get_file_name

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties


def checkValidId(uid):
    if not uid or not isinstance(uid, six.string_types):
        raise ValueError('Empty or invalid id specified', uid)

    if uid in ('.', '..'):
        msg = 'The id "%s" is invalid because it is not traversable.' % uid
        raise ValueError(msg)

    if '/' in uid:
        raise ValueError('The id "%s" contains characters illegal.' % uid)


def get_context_name(context):
    if INamedContainer.providedBy(context):
        result = context.name
    else:
        result = get_file_name(context)
    return result


@interface.implementer(IContentFolder, IContentTypeAware)
class ContentFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer,
                    CreatedAndModifiedTimeMixin):
    createDirectFieldProperties(IContentFolder)

    __parent__ = None

    name = alias('__name__')

    tags = None
    creator = None
    parameters = {}

    mimeType = mime_type = 'application/vnd.nextthought.contentfolder'

    path = None  # BWC

    def __init__(self, *args, **kwargs):
        super(ContentFolder, self).__init__()
        self.name = kwargs.get('name')
        self.title = kwargs.get('title') or self.name
        self.use_blobs = kwargs.get('use_blobs', True)
        self.filename = kwargs.get('filename') or self.name
        self.description = kwargs.get('description') or self.title

    @readproperty
    def filename(self):
        return self.name

    def _save(self, key, value):
        checkValidId(key)
        self._setitemf(key, value)
        locate(value, parent=self, name=key)
        if      IConnection(value, None) is None \
            and IConnection(self, None) is not None:
            IConnection(self).add(value)
        lifecycleevent.added(value, self, key)
        self.updateLastMod()
        self._p_changed = True  # changed

    def __setitem__(self, key, value):
        self._save(key, value)

    def add(self, obj):
        name = get_context_name(obj)
        if not name:
            raise ValueError("Cannot get file name")
        if name in self:
            del self[name]
        self[name] = obj
        return obj
    append = add

    def _eject(self, key):
        self._delitemf(key)
        self.updateLastMod()
        self._p_changed = True

    def __delitem__(self, key):
        self._eject(key)

    def remove(self, obj):
        name = get_context_name(obj)
        if not name:
            return False
        if name in self:
            del self[name]
            return True
        return False

    def rename(self, old, new):
        assert isinstance(old, six.string_types) \
            or INamedContainer.providedBy(old) \
            or IFile.providedBy(old)

        name = get_context_name(old) or old
        item = self._delitemf(name, event=False)
        item.__name__ = item.name = new  # set new name
        self._setitemf(new, item)

        def _update(obj):
            try:
                obj.updateLastMod()
            except AttributeError:
                pass
        _update(item)
        _update(self)

    def moveTo(self, item, target, newName=None):
        assert isinstance(item, six.string_types) \
            or INamedContainer.providedBy(item) \
            or IFile.providedBy(item)

        assert INamedContainer.providedBy(target)
        if self == target:
            return False

        # check item exists in this continer
        name = get_context_name(item) or item
        if name not in self:
            return False
        newName = newName or name

        # remove from target if found
        if newName in target:
            del target[newName]

        item = self._delitemf(name, event=False)
        item.__name__ = item.name = newName  # set new name
        target._setitemf(newName, item)
        lifecycleevent.moved(item, self, name, target, newName)
        item.__parent__ = target  # set lineage
        self.updateLastMod()  # update
        return True

    def copyTo(self, item, target=None, newName=None):
        target = self if target is None else target
        assert isinstance(item, six.string_types) or IFile.providedBy(item)
        assert INamedContainer.providedBy(target)

        # check item exists in this continer
        name = get_context_name(item) or item
        if name not in self:
            raise KeyError("Could not find source file")
        newName = newName or name

        # no copy
        if self == target and newName == name:
            return item

        # create new file
        item = self[name]
        newObject = item.__class__()
        for key, value in item.__dict__.items():
            if not key.startswith('_') and key not in ('data',):
                try:
                    setattr(newObject, key, value)
                except (AttributeError, TypeError):  # ignore readonly
                    pass
        newObject.name = newName  # set name
        newObject.data = item.data  # set data
        target.add(newObject)
        return newObject

    @CachedProperty('__parent__', '__name__')
    def path(self):
        return compute_path(self)

    def __str__(self):
        return "%s(%r)" % (self.__class__.__name__, self.name)
    __repr__ = __str__

    # compatible methods

    def getChildNamed(self, key):
        try:
            result = self[key]
        except KeyError:
            result = None
        return result
    get_child_named = getChildNamed

    def enumerateChildren(self):
        return tuple(self.keys())
    enumerate_children = enumerateChildren


@interface.implementer(IRootFolder)
class RootFolder(ContentFolder):
    createDirectFieldProperties(IRootFolder)

    __external_can_create__ = False

    creator = system_user.id
    mimeType = mime_type = 'application/vnd.nextthought.contentrootfolder'

    def __init__(self, *args, **kwargs):
        kwargs['name'] = kwargs.get('name') or u'root'
        super(RootFolder, self).__init__(*args, **kwargs)


def get_key(context):
    path = []
    max_depth = 99
    current = context
    while current is not None:
        if IS3RootFolder.providedBy(current):
            if path:
                path.reverse()
                result = ('/').join(path)
                return result + u'/' if IS3ContentFolder.providedBy(context) else result
            else:
                return ''
        path.append(current.__name__)
        current = current.__parent__
        max_depth -= 1
        if max_depth < 1:
            raise TypeError("Maximum location depth exceeded, probably due to a a location cycle.")

    raise TypeError("Not enough context to determine location root")


def get_src_target_keys(srcParent, srcName, targetParent, targetName):
    if srcParent == targetParent:
        parentKey = get_key(srcParent)
        srcKey = parentKey + srcName
        targetKey = parentKey + targetName
    else:
        srcKey = get_key(srcParent) + srcName
        targetKey = get_key(targetParent) + targetName

    if IS3ContentFolder.providedBy(targetParent[targetName]):
        srcKey = srcKey + '/'
        targetKey = targetKey + '/'
    return srcKey, targetKey


boto_s3 = getattr(boto, 's3')

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

    def _connection(self, debug=True):
        connection = boto.connect_s3(aws_access_key_id=self.aws_access_key_id,
                                     aws_secret_access_key=self.aws_secret_access_key)
        connection.debug = debug
        return connection

    def save_key(self, key, data='', debug=True):
        """
        Create file or Folder.
        """
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = boto_s3.key.Key(bucket)
            k.key = key
            k.set_contents_from_string(data, policy=self.grant)
        finally:
            connection.close()

    def remove_key(self, key, debug=True):
        """
        Delete file or Folder, key starts with '/' represents folder.
        """
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            if key.endswith('/'):
                keys = [x.key for x in bucket.list(prefix=key)]
                bucket.delete_keys(keys)
            else:
                bucket.delete_key(key)
        finally:
            connection.close()
        return True

    def rename_key(self, oldKey, newKey, debug=True):
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = bucket.lookup(oldKey)
            if k:
                if oldKey.endswith('/'):
                    for k in bucket.list(prefix=oldKey):
                        n = newKey + k.key[len(oldKey):]
                        k.copy(self.bucket_name, n)
                        k.delete()
                else:
                    k.copy(self.bucket_name, newKey)
                    k.delete()
        finally:
            connection.close()

    def move_key(self, srcKey, targetKey, debug=True):
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            k = bucket.lookup(srcKey)
            if k:
                if srcKey.endswith('/'):
                    for k in bucket.list(prefix=srcKey):
                        n = targetKey + k.key[len(srcKey):]
                        bucket.delete_key(n)
                        k.copy(self.bucket_name, n)
                        k.delete()
                else:
                    bucket.delete_key(targetKey)
                    k.copy(self.bucket_name, targetKey)
                    k.delete()
        finally:
            connection.close()

    def clear_keys(self, parentKey, debug=True):
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name)
            keys = [x.key for x in bucket.list(prefix=parentKey) if x.key != parentKey]
            bucket.delete_keys(keys)
        finally:
            connection.close()

    def to_external_s3_href(self, key=None, obj=None, debug=True):
        key = get_key(obj) if obj else key
        connection = self._connection(debug)
        try:
            bucket = connection.get_bucket(self.bucket_name, validate=False)
            k = boto_s3.key.Key(bucket, key)
            return k.generate_url(expires_in=0, query_auth=False)
        finally:
            connection.close()


@interface.implementer(IS3ContentFolder)
class S3ContentFolder(ContentFolder, BotoS3Mixin):

    createDirectFieldProperties(IS3ContentFolder)

    mimeType = mime_type = 'application/vnd.nextthought.s3contentfolder'

    def __init__(self, *args, **kwargs):
        super(S3ContentFolder, self).__init__(*args, **kwargs)

    def add(self, obj):
        obj = super(S3ContentFolder, self).add(obj)
        self.save_key(key=get_key(obj),
                      data=obj.data if not IS3ContentFolder.providedBy(obj) else '')
        return obj

    def remove(self, obj):
        key = get_key(obj)
        result = super(S3ContentFolder, self).remove(obj)
        if key and result:
            result = self.remove_key(key=key)
        return result

    def rename(self, old, new):
        oldName = get_context_name(old) or old
        super(S3ContentFolder, self).rename(oldName, new)

        oldKey, newKey = get_src_target_keys(self, oldName, self, new)
        self.rename_key(oldKey, newKey)

    def moveTo(self, item, target, newName=None):
        name = get_context_name(item) or item
        newName = newName or name
        if super(S3ContentFolder, self).moveTo(item, target, newName):
            if self != target or name != newName:
                srcKey, targetKey = get_src_target_keys(self, name, target, newName)
                self.move_key(srcKey=srcKey,
                              targetKey=targetKey)
            return True
        return False

    def clear(self):
        super(S3ContentFolder, self).clear()
        parentKey = get_key(self)
        self.clear_keys(parentKey)


@interface.implementer(IS3RootFolder)
class S3RootFolder(S3ContentFolder, RootFolder):

    createDirectFieldProperties(IS3RootFolder)

    __external_can_create__ = False

    creator = system_user.id
    mimeType = mime_type = 'application/vnd.nextthought.s3contentrootfolder'

    def __init__(self, *args, **kwargs):
        kwargs['name'] = kwargs.get('name') or u'root'
        super(S3RootFolder, self).__init__(*args, **kwargs)
