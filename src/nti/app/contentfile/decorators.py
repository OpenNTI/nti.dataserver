#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.location.interfaces import ILocation

from plone.namedfile.interfaces import IFile

from nti.app.contentfile.view_mixins import download_file_name
from nti.app.contentfile.view_mixins import to_external_oid_and_link

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

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
        oid, link = to_external_oid_and_link(item, name=None, render=True)
        if oid:
            name = download_file_name(item)
            for element, key in ('view', 'url'), ('download', 'download_url'):
                href = link + '/@@' + element
                if element == 'view':
                    href += ('/' + name if name else u'')
                ext_dict[key] = href
            # XXX: make sure we add OID/NTIID fields to signal this file
            # can be marked as an internal ref if it's going to be updated
            if OID not in ext_dict:
                ext_dict[OID] = oid
            if NTIID not in ext_dict:
                ext_dict[NTIID] = oid
        else:
            ext_dict['url'] = None
            ext_dict['download_url'] = None
        ext_dict.pop('parameters', None)
        ext_dict['value'] = ext_dict['url']
        ext_dict['size'] = item.getSize()


@component.adapter(IFileConstrained)
@interface.implementer(IExternalObjectDecorator)
class _FileConstrainedDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context, rel="FileConstrains",
                    elements='@@constrains', method='GET')
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)
