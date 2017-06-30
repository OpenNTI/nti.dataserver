#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.location.interfaces import ILocation

from plone.namedfile.interfaces import IFile

from nti.app.contentfile.interfaces import IExternalLinkProvider

from nti.app.contentfile.view_mixins import download_file_name
from nti.app.contentfile.view_mixins import to_external_oid_and_link

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.oids import to_external_ntiid_oid

from nti.externalization.singleton import SingletonDecorator

from nti.links.links import Link

from nti.namedfile.interfaces import IFileConstrained

OID = StandardExternalFields.OID
LINKS = StandardExternalFields.LINKS
NTIID = StandardExternalFields.NTIID


@component.adapter(IFile)
@interface.implementer(IExternalMappingDecorator)
class _ContentFileDecorator(object):

    __metaclass__ = SingletonDecorator

    def decorateExternalMapping(self, item, ext_dict):
        # get link. this should add object to connection if required
        # This provides our download link.
        link = IExternalLinkProvider(item).link()
        ext_dict['download_url'] = link if link else None
        view_parts = to_external_oid_and_link(item)
        if view_parts and view_parts[1]:
            name = download_file_name(item) or ''
            view_url = '%s/%s' % (view_parts[1], name)
            ext_dict['url'] = view_url
        else:
            ext_dict['url'] = None
        # XXX: make sure we add OID/NTIID fields to signal this file
        # can be marked as an internal ref if it's going to be updated
        oid = to_external_ntiid_oid(item)
        if OID not in ext_dict:
            ext_dict[OID] = oid
        if NTIID not in ext_dict:
            ext_dict[NTIID] = oid
        ext_dict.pop('parameters', None)
        ext_dict['value'] = ext_dict['url']
        ext_dict['size'] = item.getSize()


@component.adapter(IFileConstrained)
@interface.implementer(IExternalObjectDecorator)
class _FileConstrainedDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context,
                    rel="FileConstrains",
                    elements='@@constrains',
                    method='GET')
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)
