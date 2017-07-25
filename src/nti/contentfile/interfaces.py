#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.location.interfaces import IContained

from nti.base.interfaces import INamedFile as IBaseNamedFile

from nti.namedfile.interfaces import INamedFile
from nti.namedfile.interfaces import INamedImage
from nti.namedfile.interfaces import INamedBlobFile
from nti.namedfile.interfaces import INamedBlobImage

from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine


class IContentBaseFile(IBaseNamedFile, IAttributeAnnotatable, IContained):

    tags = ListOrTuple(ValidTextLine(title=u"A single tag"), required=False)

    name = ValidTextLine(title=u"Identifier for the file", required=True)

    def add_association(context):
        """
        add a associatied object to this file
        """

    def remove_association(context):
        """
        remove an associatied object from this file
        """

    def clear_associations():
        """
        remove all associatied object from this file
        """

    def associations():
        """
        return an iterable with the associatied objects
        """

    def has_associations():
        """
        return if this object has any associations
        """
IBaseFile = IContentBaseFile  # BWC


# named objects


class IContentFile(INamedFile, IContentBaseFile):
    pass


class IContentImage(INamedImage, IContentBaseFile):
    pass


class IContentBlobFile(INamedBlobFile, IContentBaseFile):
    pass


class IContentBlobImage(INamedBlobImage, IContentBaseFile):
    pass


# s3 objects


class IS3File(IContentBaseFile):

    def invalidate():
        """
        Invalidate this object
        """


class IS3Image(IS3File):

    def getImageSize():
        """
        Return a tuple (x, y) that describes the dimensions of
        the object.
        """


class IS3FileIO(interface.Interface):
    """
    An adapter to do basic operations on a :class:`.IS3Object`
    """

    def key():
        """
        return the key of the object
        """

    def exists():
        """
        return if object exists
        """

    def contents():
        """
        return the contents of the object
        """
        
    def size():
        """
        return the contents size of the object
        """

    def save():
        """
        saves contents of the object
        """

    def remove(key=None):
        """
        Delete the object or the specified key
        """

    def rename(key, target):
        """
        renames the object
        """

    def to_external_s3_href(obj):
        """
        return the url/href for the specified object
        """
