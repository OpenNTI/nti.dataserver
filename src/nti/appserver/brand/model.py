#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.traversing.api import joinPath

from nti.appserver.brand.interfaces import ISiteBrand
from nti.appserver.brand.interfaces import ISiteBrandImage
from nti.appserver.brand.interfaces import ISiteBrandAssets
from nti.appserver.brand.interfaces import ISiteAssetsFileSystemLocation

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

logger = __import__('logging').getLogger(__name__)


@WithRepr
@interface.implementer(ISiteBrand)
class SiteBrand(PersistentCreatedAndModifiedTimeObject,
                SchemaConfigured):

    createDirectFieldProperties(ISiteBrand)

    __parent__ = None
    __name__ = alias('Name')

    _theme = None

    creator = None
    name = alias('Name')
    mimeType = mime_type = 'application/vnd.nextthought.sitebrand'

    @property
    def theme(self):
        return dict(self._theme) if self._theme else {}

    @theme.setter
    def theme(self, nv):
        pass

    @Lazy
    def brand_name(self):
        policy = component.queryUtility(ISitePolicyUserEventListener)
        return getattr(policy, 'BRAND', '')


@WithRepr
@interface.implementer(ISiteBrandAssets)
class SiteBrandAssets(PersistentCreatedAndModifiedTimeObject,
                      SchemaConfigured):

    createDirectFieldProperties(ISiteBrandAssets)

    __parent__ = None
    __name__ = 'SiteBrandAssets'

    creator = None
    mimeType = mime_type = 'application/vnd.nextthought.sitebrandassets'


@WithRepr
@interface.implementer(ISiteBrandImage)
class SiteBrandImage(PersistentCreatedAndModifiedTimeObject,
                     SchemaConfigured):

    createDirectFieldProperties(ISiteBrandAssets)

    __parent__ = None
    __name__ = alias('Name')

    creator = None
    name = alias('Name')
    mimeType = mime_type = 'application/vnd.nextthought.sitebrandimage'

    @property
    def href(self):
        result = self.source
        if self.key is not None:
            # If we have a key, we are a relative path to a disk location.
            # Otherwise, we are empty or have a full URL to an external image.
            location = component.queryUtility(ISiteAssetsFileSystemLocation)
            if location is not None and self.__parent__:
                asset_part = self.__parent__.root.name
                __traceback_info__ = location.prefix, asset_part, self.key.name
                prefix = location.prefix
                if prefix.startswith('/'):
                    prefix = prefix[1:]
                if prefix.endswith('/'):
                    prefix = prefix[:-1]
                result = joinPath('/', prefix, self.key.name)
        return result

    @href.setter
    def href(self, nv):
        pass

