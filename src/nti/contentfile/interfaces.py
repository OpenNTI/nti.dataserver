#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.location.interfaces import IContained

from nti.namedfile.interfaces import IFile
from nti.namedfile.interfaces import INamedFile
from nti.namedfile.interfaces import INamedImage
from nti.namedfile.interfaces import INamedBlobFile
from nti.namedfile.interfaces import INamedBlobImage

from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine


class IContentBaseFile(IFile, IAttributeAnnotatable, IContained):

    tags = ListOrTuple(ValidTextLine(title="A single tag"), required=False)

    name = ValidTextLine(title="Identifier for the file", required=True)

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


class IContentFile(INamedFile, IContentBaseFile):
    pass


class IContentImage(INamedImage, IContentBaseFile):
    pass


class IContentBlobFile(INamedBlobFile, IContentBaseFile):
    pass


class IContentBlobImage(INamedBlobImage, IContentBaseFile):
    pass
