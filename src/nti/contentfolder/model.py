#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import CachedProperty

from zope.event import notify

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

from nti.contentfolder.interfaces import S3ObjectCleared
from nti.contentfolder.interfaces import S3ObjectEjected
from nti.contentfolder.interfaces import S3ObjectRenamed

from nti.contentfolder.utils import compute_path

from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin

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
    return getattr(context, 'filename', None) or context


@interface.implementer(IContentFolder, IContentTypeAware)
class ContentFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer,
                    CreatedAndModifiedTimeMixin):
    createDirectFieldProperties(IContentFolder)

    __parent__ = None

    filename = name = alias('__name__')

    tags = None
    creator = None
    parameters = {}

    mimeType = mime_type = 'application/vnd.nextthought.contentfolder'

    path = None  # BWC

    def __init__(self,  **kwargs):
        super(ContentFolder, self).__init__()
        self.name = kwargs.get('name') or kwargs.get('filename')
        self.title = kwargs.get('title') or self.name
        self.description = kwargs.get('description') or self.title

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
            raise ValueError("Cannot get a file name")
        if name in self:
            del self[name]
        self[name] = obj
        return obj
    append = add

    def _eject(self, key, event=True):
        item = self._delitemf(key, event)
        self.updateLastMod()
        self._p_changed = True
        return item

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

        name = get_context_name(old)
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
        return item

    def moveTo(self, item, target, newName=None):
        assert isinstance(item, six.string_types) \
            or INamedContainer.providedBy(item) \
            or IFile.providedBy(item)

        assert INamedContainer.providedBy(target)
        if self == target:
            return False

        # check item exists in this continer
        name = get_context_name(item)
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
        name = get_context_name(item)
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
        newObject.__name__ = newObject.name = newName  # set name
        newObject.data = item.data  # set data
        target.add(newObject)
        return newObject

    @CachedProperty('__parent__', '__name__')
    def path(self):
        return compute_path(self)

    def __str__(self):
        return "%s(%r)" % (self.__class__.__name__, self.__name__)
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
        kwargs['filename'] = kwargs.get('filename') or kwargs.get('name') or u'root'
        super(RootFolder, self).__init__(*args, **kwargs)


@interface.implementer(IS3ContentFolder)
class S3ContentFolder(ContentFolder):
    createDirectFieldProperties(IS3ContentFolder)

    mimeType = mime_type = 'application/vnd.nextthought.s3contentfolder'

    def rename(self, old, new):
        old_name = get_context_name(old)
        item = super(S3ContentFolder, self).rename(old_name, new)
        notify(S3ObjectRenamed(item, old_name, new))
        return item

    def clear(self):
        super(S3ContentFolder, self).clear()
        notify(S3ObjectCleared(self))

    def eject(self, key):
        if key not in self:
            raise KeyError(key)
        item = self._eject(key, False)
        notify(S3ObjectEjected(item))
        return item


@interface.implementer(IS3RootFolder)
class S3RootFolder(S3ContentFolder, RootFolder):
    createDirectFieldProperties(IS3RootFolder)

    __external_can_create__ = False

    creator = system_user.id
    mimeType = mime_type = 'application/vnd.nextthought.s3contentrootfolder'

    def __init__(self, *args, **kwargs):
        kwargs['filename'] = kwargs.get('filename') or kwargs.get('name') or u'root'
        super(S3RootFolder, self).__init__(*args, **kwargs)
