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

from zope.container.constraints import contains
from zope.container.constraints import containers

from zope.container.interfaces import IContained
from zope.container.interfaces import IContentContainer

from zope.dublincore.interfaces import IDCDescriptiveProperties

from nti.base.interfaces import IFile
from nti.base.interfaces import ICreated
from nti.base.interfaces import ILastModified

from nti.schema.field import Bool
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine


class INamedContainer(IContained,
                      IDCDescriptiveProperties,
                      IContentContainer,
                      ILastModified,
                      ICreated):
    tags = ListOrTuple(ValidTextLine(title=u"A single tag"), required=False)

    name = ValidTextLine(title=u"Folder URL-safe name", required=True)

    filename = ValidTextLine(title=u"Folder name", required=True)

    # dublin core
    title = ValidTextLine(title=u"Folder title",
                          required=False,
                          default=None)

    description = ValidTextLine(title=u"Folder description",
                                required=False,
                                default=None)

    use_blobs = Bool(title=u"Use blobs flag", required=True, default=True)
    use_blobs.setTaggedValue('_ext_excluded_out', True)


class IContentFolder(INamedContainer, IAttributeAnnotatable):

    containers('.INamedContainer')
    contains('.INamedContainer',
             IFile)

    __parent__.required = False
    __setitem__.__doc__ = None

    def add(obj):
        """
        add an object to this container
        """

    def remove(obj):
        """
        remove the specified object from this container
        """

    def rename(old, new):
        """
        rename an stored item
        """

    def moveTo(item, target, newName=None):
        """
        move the specified item to the target with a possible new name
        """

    def copyTo(item, target, newName=None):
        """
        copy the specified item to the target with a possible new name
        """


class IRootFolder(IContentFolder):
    pass


class ILockedFolder(IContentFolder):
    pass


class IS3ContentFolder(IContentFolder):
    pass


class IS3RootFolder(IS3ContentFolder, IRootFolder):
    pass


class IS3LockedFolder(IS3ContentFolder, ILockedFolder):
    pass


# Index adapters


class ISiteAdapter(interface.Interface):
    """
    Adapt resource objects to their site
    """
    site = interface.Attribute("site string")


class IMimeTypeAdapter(interface.Interface):
    """
    Adapt resource objects to their mimetype
    """
    mimeType = interface.Attribute("MimeType string")


class IContainerIdAdapter(interface.Interface):
    """
    Adapt resource objects to their containerId
    """
    containerId = interface.Attribute("containerId string")


class IPathAdapter(interface.Interface):
    """
    Adapt resource objects to their path
    """
    path = interface.Attribute("site string")


class INameAdapter(interface.Interface):
    """
    Adapt resource objects to their name
    """
    name = interface.Attribute("name string")


class IFilenameAdapter(interface.Interface):
    """
    Adapt resource objects to their filename
    """
    filename = interface.Attribute("filename string")


class IAssociationsAdapter(interface.Interface):
    """
    Adapt resource objects to their associations
    """
    associations = interface.Attribute("Associations ids")
