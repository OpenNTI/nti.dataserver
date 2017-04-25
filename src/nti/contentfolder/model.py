#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import readproperty
from zope.cachedescriptors.property import CachedProperty

from zope.location.location import locate

from zope.mimetype.interfaces import IContentTypeAware

from zope.security.management import system_user

from ZODB.interfaces import IConnection

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import IContentFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.contentfolder.utils import compute_path

from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin

from nti.namedfile.file import get_file_name

from nti.namedfile.interfaces import IFile

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties


def checkValidId(uid):
    if not uid or not isinstance(uid, six.string_types):
        raise ValueError('Empty or invalid id specified', uid)

    if uid in ('.', '..'):
        raise ValueError(
            'The id "%s" is invalid because it is not traversable.' % uid)

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
    mimeType = mime_type = str('application/vnd.nextthought.contentfolder')

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
    mimeType = mime_type = str('application/vnd.nextthought.contentrootfolder')

    def __init__(self, *args, **kwargs):
        kwargs['name'] = kwargs.get('name') or 'root'
        super(RootFolder, self).__init__(*args, **kwargs)
