#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to working with enclosures.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope.location.location import LocationProxy

from pyramid import traversal

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.internalization import class_name_from_content_type

from nti.app.externalization.view_mixins import UploadRequestUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.appserver import httpexceptions as hexc

from nti.dataserver import enclosures

from nti.dataserver.interfaces import IEnclosedContent
from nti.dataserver.interfaces import ISimpleEnclosureContainer

from nti.mimetype.mimetype import MIME_BASE
from nti.mimetype.mimetype import nti_mimetype_from_object

from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.internalization import find_factory_for


def _force_update_modification_time(obj, lastModified, max_depth=-1):
    """
    Traverse up the parent tree (up to `max_depth` times) updating modification times.
    """
    if hasattr(obj, 'updateLastMod'):
        obj.updateLastMod(lastModified)

    if max_depth == 0:
        return
    if max_depth > 0:
        max_depth = max_depth - 1

    parent = getattr(obj, '__parent__', None)
    if parent is None:
        return
    _force_update_modification_time(parent, lastModified, max_depth)


class EnclosurePostView(AbstractAuthenticatedView,
                        UploadRequestUtilsMixin,
                        ModeledContentUploadRequestUtilsMixin):
    """
    View for creating new enclosures.
    """

    def __call__(self):
        # A _AbstractObjectResource OR an ISimpleEnclosureContainer
        context = self.request.context
        # Enclosure containers are defined to be IContainerNamesContainer,
        # which means they will choose their name based on what we give them
        if ISimpleEnclosureContainer.providedBy(context):
            enclosure_container = context
        else:
            enclosure_container = getattr(context, 'resource', None)

        if enclosure_container is None:
            # Posting data to something that cannot take it. This was probably
            # actually meant to be a PUT to update existing data
            raise hexc.HTTPForbidden("Cannot POST here. Did you mean to PUT?")

        content_type = self._get_body_type()
        # Chop a trailing '+json' off if present
        if '+' in content_type:
            content_type = content_type[0:content_type.index('+')]

        # First, see if they're giving us something we can model
        datatype = class_name_from_content_type(content_type)
        datatype = datatype + 's' if datatype else None
        # Pass in all the information we have, as if it was a full externalized
        # object
        modeled_content = find_factory_for({StandardExternalFields.MIMETYPE: content_type,
                                            StandardExternalFields.CLASS: datatype})
        if modeled_content:
            modeled_content = modeled_content()
        #modeled_content = self.dataserver.create_content_type( datatype, create_missing=False )
        # if not getattr( modeled_content, '__external_can_create__', False ):
        #    modeled_content = None

        if modeled_content is not None:
            modeled_content.creator = self.getRemoteUser()
            self.updateContentObject(modeled_content,
                                     self.readInput(self._get_body_content()),
                                     set_id=True)
            modeled_content.containerId = getattr(enclosure_container, 'id', None) \
                                       or getattr(enclosure_container, 'ID')  # TODO: Assumptions
            content_type = nti_mimetype_from_object(modeled_content)

        content = modeled_content if modeled_content is not None else self._get_body_content()
        if content is not modeled_content and content_type.startswith(MIME_BASE):
            # If they tried to send us something to model, but we didn't actually
            # model it, then screw that, it's just a blob
            content_type = 'application/octet-stream'
            # OTOH, it would be nice to not have to
            # replicate the content type into the enclosure object when we
            # create it. We should delay until later. This means we need a new
            # enclosure object

        enclosure = enclosures.SimplePersistentEnclosure(self._get_body_name(),
                                                         content,
                                                         content_type)
        enclosure.creator = self.getRemoteUser()
        enclosure_container.add_enclosure(enclosure)

        # Ensure we'll be able to get a OID
        if getattr(enclosure_container, '_p_jar', None):
            if modeled_content is not None:
                enclosure_container._p_jar.add(modeled_content)
            enclosure_container._p_jar.add(enclosure)

        # TODO: Creating enclosures generally doesn't update the modification time
        # of its container. It arguably should. Since we currently report a few levels
        # of the tree at once, though, (classes AND their sections) it is necessary
        # to update a few levels at once. This is wrong and increases the chance of conflicts.
        # The right thing is to stop doing that.
        _force_update_modification_time(enclosure_container,
                                        enclosure.lastModified)

        self.request.response.status_int = 201  # Created
        # If we're doing a form submission, then the browser (damn IE)
        # will try to follow this location if we send it
        # which results in annoying and useless dialogs
        if self._find_file_field() is None:
            proxy = LocationProxy(enclosure, context, enclosure.name)
            self.request.response.location = self.request.resource_url(proxy)
        # TODO: We need to return some representation of this object
        # just created. We need an 'Entry' wrapper.
        return enclosure


class EnclosurePutView(AbstractAuthenticatedView,
                       UploadRequestUtilsMixin,
                       ModeledContentUploadRequestUtilsMixin):
    """
    View for editing an existing enclosure.
    """

    def __call__(self):
        context = self.request.context
        assert IEnclosedContent.providedBy(context)
        # How should we be dealing with changes to Content-Type?
        # Changes to Slug are not allowed because that would change the URL
        # Not modeled # TODO: Check IModeledContent.providedBy( context.data )?
        # FIXME: See comments in _EnclosurePostView about mod times.
        if not context.mime_type.startswith(MIME_BASE):
            context.data = self._get_body_content()
            _force_update_modification_time(context, time.time())
            result = hexc.HTTPNoContent()
        else:
            modeled_content = context.data
            self.updateContentObject(modeled_content,
                                     self.readInput(self._get_body_content()))
            result = modeled_content
            _force_update_modification_time(context,
                                            modeled_content.lastModified)
        return result


class EnclosureDeleteView(AbstractAuthenticatedView):
    """
    View for deleting an object.
    """

    def __call__(self):
        context = self.request.context
        assert IEnclosedContent.providedBy(context)
        container = traversal.find_interface(context,
                                             ISimpleEnclosureContainer)
        # TODO: Handle the KeyError here and also if ISimpleEnclosureContainer
        # was not found
        # should fire lifecycleevent.removed
        container.del_enclosure(context.name)
        result = hexc.HTTPNoContent()
        return result
