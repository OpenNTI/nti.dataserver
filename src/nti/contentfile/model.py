#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from six import StringIO

from zope import interface

from zope.cachedescriptors.property import CachedProperty

from BTrees.OOBTree import OOTreeSet

from nti.contentfile.interfaces import IContentFile
from nti.contentfile.interfaces import IContentImage
from nti.contentfile.interfaces import IContentBlobFile
from nti.contentfile.interfaces import IContentBlobImage

from nti.namedfile.file import NamedFile
from nti.namedfile.file import NamedImage
from nti.namedfile.file import NamedBlobFile
from nti.namedfile.file import NamedBlobImage

from nti.namedfile.interfaces import IInternalFileRef

from nti.property.property import Lazy
from nti.property.property import alias

from nti.wref.interfaces import IWeakRef


class BaseContentMixin(object):

    tags = ()
    creator = None

    path = None  # XXX BWC

    __parent__ = None
    __name__ = alias('name')

    def __init__(self, *args, **kwargs):
        super(BaseContentMixin, self).__init__(*args, **kwargs)

    # associations

    def _lazy_create_ootreeset_for_wref(self):
        self._p_changed = True
        result = OOTreeSet()
        if self._p_jar:
            self._p_jar.add(result)
        return result

    def discard(self, container, value):
        try:
            container.discard(value)
        except AttributeError:
            try:
                container.remove(value)
            except (KeyError, ValueError):
                pass

    def _remove_from_named_lazy_set_of_wrefs(self, name, context):
        self._p_activate()
        if name in self.__dict__:
            jar = getattr(self, '_p_jar', None)
            container = getattr(self, name)
            if jar is not None:
                jar.readCurrent(self)
                container._p_activate()
                jar.readCurrent(container)
            wref = IWeakRef(context, None)
            if wref is not None:
                __traceback_info__ = context, wref
                self.discard(container, wref)

    @Lazy
    def _associations(self):
        return self._lazy_create_ootreeset_for_wref()

    def add_association(self, context):
        wref = IWeakRef(context, None)
        if wref is not None:
            self._associations.add(wref)
            return True
        return False

    def remove_association(self, context):
        self._remove_from_named_lazy_set_of_wrefs('_associations', context)

    def associations(self):
        for wref in self._associations:
            try:
                obj = wref()
                if obj is not None:
                    yield obj
            except Exception:
                logger.exception("Error while getting associatied object")

    def has_associations(self):
        return  bool(   '_associations' in self.__dict__ 
                     and self._associations)

    def count_associations(self):
        result = 0
        if '_associations' in self.__dict__:
            result = len(list(self.associations()))
        return result

    def validate_associations(self):
        if not '_associations' in self.__dict__:
            return
        for wref in list(self._associations):
            try:
                obj = wref()
                if obj is None:
                    self.discard(self._associations, wref)
            except Exception:
                logger.exception("Error while getting associatied object")

    def clear_associations(self):
        if '_associations' in self.__dict__:
            self._associations.clear()

    # IFileReader
    
    @CachedProperty('data')
    def _v_fp(self):
        return StringIO(self.data)

    def read(self, size=-1):
        return self._v_fp.read(size) if size != -1 else self.data

    def seek(self, offset, whence=0):
        return self._v_fp.seek(offset, whence)

    def tell(self):
        return self._v_fp.tell()

    # compatible methods

    def readContents(self):
        return self.data
BaseMixin = BaseContentMixin  # BWC


@interface.implementer(IContentFile)
class ContentFile(BaseContentMixin, NamedFile):
    pass


@interface.implementer(IContentBlobFile)
class ContentBlobFile(BaseContentMixin, NamedBlobFile):
    pass


@interface.implementer(IContentImage)
class ContentImage(BaseContentMixin, NamedImage):
    pass


@interface.implementer(IContentBlobImage)
class ContentBlobImage(BaseContentMixin, NamedBlobImage):
    pass


def transform_to_blob(context, associations=False):
    if IContentFile.providedBy(context):
        result = ContentBlobFile()
    elif IContentImage.providedBy(context):
        result = ContentBlobImage()
    else:
        result = context
    if result is not context:
        for key, value in context.__dict__.items():
            if not key.startswith('_') and key != 'data':
                try:
                    setattr(result, key, value)
                except (AttributeError, TypeError):  # ignore readonly
                    pass
        result.data = context.data  # be explicit
        if IInternalFileRef.providedBy(context):
            interface.alsoProvides(result, IInternalFileRef)
            result.reference = getattr(context,
                                       'reference', 
                                       None)  # extra check
        if context.has_associations() or associations:
            [result.add_association(obj) for obj in context.associations()]
    return result
