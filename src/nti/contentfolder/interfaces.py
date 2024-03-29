#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.container.constraints import contains
from zope.container.constraints import containers

from zope.container.interfaces import IContained
from zope.container.interfaces import IContentContainer

from zope.dublincore.interfaces import IDCDescriptiveProperties

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from nti.base.interfaces import IFile
from nti.base.interfaces import ICreated
from nti.base.interfaces import ILastModified

from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine


class INamedContainer(IContained,
                      IDCDescriptiveProperties,
                      IContentContainer,
                      ILastModified,
                      ICreated):

    tags = ListOrTuple(ValidTextLine(title=u"A single tag"), required=False)

    filename = ValidTextLine(title=u"Folder name", required=True)

    # dublin core
    title = ValidTextLine(title=u"Folder title",
                          required=False,
                          default=None)

    description = ValidTextLine(title=u"Folder description",
                                required=False,
                                default=None)


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

    def eject(key):
        """
        remove the item with the specified key w/o generating a removed event
        """


class IS3RootFolder(IS3ContentFolder, IRootFolder):
    pass


class IS3LockedFolder(IS3ContentFolder, ILockedFolder):
    pass


# events


class IS3ObjectRenamed(IObjectEvent):
    source = interface.Attribute("Renamed object")
    old_name = interface.Attribute("old name")
    new_name = interface.Attribute("new name")


@interface.implementer(IS3ObjectRenamed)
class S3ObjectRenamed(ObjectEvent):

    def __init__(self,  obj, old_name, new_name):
        super(S3ObjectRenamed, self).__init__(obj)
        self.old_name = old_name
        self.new_name = new_name

    @property
    def source(self):
        return self.object


class IS3ObjectCleared(IObjectEvent):
    pass


@interface.implementer(IS3ObjectCleared)
class S3ObjectCleared(ObjectEvent):
    pass


class IS3ObjectEjected(IObjectEvent):
    pass


@interface.implementer(IS3ObjectEjected)
class S3ObjectEjected(ObjectEvent):
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


class IContentResources(interface.Interface):
    """
    An interface to return content resource objects 

    These will typically be registered as named utilities
    """

    def iter_objects():
        pass


def get_content_resources():
    predicates = component.getUtilitiesFor(IContentResources)
    for _, predicate in list(predicates):
        for obj in predicate.iter_objects():
            yield obj
