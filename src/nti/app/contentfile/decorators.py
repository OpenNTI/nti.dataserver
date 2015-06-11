#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.dataserver_core.interfaces import ILinkExternalHrefOnly

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import to_external_ntiid_oid

from nti.links.links import Link

OID = StandardExternalFields.OID
NTIID = StandardExternalFields.NTIID

@interface.implementer(IExternalMappingDecorator)
class _ContentFileDecorator(object):

    __metaclass__ = SingletonDecorator

    def decorateExternalMapping(self, item, ext_dict):
        target = to_external_ntiid_oid(item, add_to_connection=True)
        if target:
            for element, key in ('view', 'url'), ('download', 'download_url'):
                link = Link(target=target,
                            target_mime_type=item.contentType,
                            elements=(element,),
                            rel="data")
                interface.alsoProvides(link, ILinkExternalHrefOnly)
                ext_dict[key] = to_external_object(link)
            # make sure we add OID/NTIID fields to signal this file
            # can mark as an internal ref if it's going to be updated
            if OID not in ext_dict:
                ext_dict[OID] = target
            if NTIID not in ext_dict:
                ext_dict[NTIID] = target
        else:
            ext_dict['url'] = None
            ext_dict['download_url'] = None
        ext_dict['value'] = ext_dict['url']
