#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.event import notify

from zope.intid.interfaces import IIntIds

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectMovedEvent

from zc.intid.interfaces import IBeforeIdRemovedEvent

from nti.app.contentfile.view_mixins import validate_sources

from nti.app.authentication import get_remote_user

from nti.contentfile.interfaces import IS3File
from nti.contentfile.interfaces import IS3FileIO
from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfolder.index import get_content_resources_catalog

from nti.contentfolder.interfaces import IContentFolder
from nti.contentfolder.interfaces import IS3ContentFolder
from nti.contentfolder.interfaces import IS3ObjectEjected
from nti.contentfolder.interfaces import IS3ObjectRenamed

from nti.transactions import transactions

logger = __import__('logging').getLogger(__name__)


@component.adapter(IContentBaseFile, IObjectAddedEvent)
def _on_content_file_added(context, event):
    if IContentFolder.providedBy(event.newParent):
        user = get_remote_user()
        validate_sources(user, event.newParent, sources=(context,))


@component.adapter(IS3ContentFolder, IObjectAddedEvent)
def _on_s3_folder_added(context, _):
    if IS3ContentFolder.providedBy(context.__parent__):
        s3 = IS3FileIO(context, None)
        if s3 is not None:
            transactions.do_near_end(target=context, call=s3.save)


@component.adapter(IS3File, IBeforeIdRemovedEvent)
def _on_s3_file_removed(context, _):
    if IS3ContentFolder.providedBy(context.__parent__):
        s3 = IS3FileIO(context, None)
        if s3 is not None:
            transactions.do_near_end(target=context,
                                     call=s3.remove,
                                     args=(s3.key(),))


@component.adapter(IS3ContentFolder, IBeforeIdRemovedEvent)
def _on_s3_folder_removed(context, event):
    _on_s3_file_removed(context, event)


def _get_src_target_keys(source_parent, source_name, target_parent, target_name):
    if source_parent == target_parent:
        parent_key = IS3FileIO(source_parent).key()
        source_key = parent_key + source_name
        target_key = parent_key + target_name
    else:
        source_key = IS3FileIO(source_parent).key() + source_name
        target_key = IS3FileIO(target_parent).key() + target_name

    # check if a folder is being renamed
    if IS3ContentFolder.providedBy(target_parent[target_name]):
        source_key = source_key + '/'
        target_key = target_key + '/'
    return source_key, target_key


@component.adapter(IS3File, IS3ObjectRenamed)
def _on_s3_file_renamed(context, event):
    old_name = event.old_name
    new_name = event.new_name
    parent = context.__parent__
    if IS3ContentFolder.providedBy(parent):
        s3 = IS3FileIO(context, None)
        if s3 is not None:
            source_key, target_key = _get_src_target_keys(parent, old_name,
                                                          parent, new_name)
            transactions.do_near_end(target=context,
                                     call=s3.rename,
                                     args=(source_key, target_key))


@component.adapter(IS3ContentFolder, IS3ObjectRenamed)
def _on_s3_folder_renamed(context, event):
    _on_s3_file_renamed(context, event)


@component.adapter(IS3File, IObjectMovedEvent)
def _on_s3_file_moved(context, event):
    if      IS3ContentFolder.providedBy(context.__parent__) \
        and event.oldParent is not None \
        and event.newParent is not None:
        s3 = IS3FileIO(context, None)
        if s3 is not None:
            source_key, target_key = _get_src_target_keys(event.oldParent, event.oldName,
                                                          event.newParent, event.newName)
            transactions.do_near_end(target=context,
                                     call=s3.rename,
                                     args=(source_key, target_key))


@component.adapter(IS3ContentFolder, IObjectMovedEvent)
def _on_s3_folder_moved(context, event):
    _on_s3_file_moved(context, event)


@component.adapter(IS3File, IS3ObjectEjected)
def _on_s3_file_ejected(context, _):
    intids = component.getUtility(IIntIds)
    # unindex
    catalog = get_content_resources_catalog()
    doc_id = intids.queryId(context)
    if doc_id is not None:
        catalog.unindex_doc(doc_id)
        intids.unregister(context)
    try:
        from nti.metadata import queue_removed
        queue_removed(context)
    except ImportError:
        pass


@component.adapter(IS3ContentFolder, IS3ObjectEjected)
def _on_s3_folder_ejected(context, event):
    _on_s3_file_ejected(context, event)
    if IS3ContentFolder.providedBy(context):
        for child in context.values():
            notify(event.__class__(child))
