#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time

from zope import component

from zope.traversing.interfaces import IEtcNamespace

from zope.intid import IIntIds

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.maps import CaseInsensitiveDict

from nti.contentlibrary.indexed_data import get_registry
from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contenttypes.presentation import PACKAGE_CONTAINER_INTERFACES

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.site.utils import unregisterUtility
from nti.site.site import get_component_hierarchy_names

from ..utils import yield_content_packages

from ..subscribers import clear_package_assets
from ..subscribers import clear_content_package_assets
from ..subscribers import clear_namespace_last_modified

from . import iface_of_thing

ITEMS = StandardExternalFields.ITEMS

def _get_package_ntiids(values):
    ntiids = values.get('ntiid') or values.get('ntiids')
    if ntiids and isinstance(ntiids, six.string_types):
        ntiids = ntiids.split()
    return ntiids

@view_config(context=IDataserverFolder)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               permission=nauth.ACT_NTI_ADMIN,
               name='GetPackagePresentationAssets')
class GetPackagePresentationAssetsView(AbstractAuthenticatedView,
                                       ModeledContentUploadRequestUtilsMixin):


    def __call__(self):
        params = CaseInsensitiveDict(self.request.params)
        ntiids = _get_package_ntiids(params)
        if not ntiids:
            packages = list(yield_content_packages(all_packages=True))
        else:
            packages = list(yield_content_packages(ntiids=ntiids))

        catalog = get_library_catalog()
        intids = component.getUtility(IIntIds)

        total = 0
        result = LocatedExternalDict()
        result[ITEMS] = items = {}
        sites = get_component_hierarchy_names()
        for package in packages:
            objects = catalog.search_objects(intids=intids,
                                             provided=PACKAGE_CONTAINER_INTERFACES,
                                             namespace=package.ntiid,
                                             sites=sites)
            items[package.ntiid] = sorted(objects or (),
                                          key=lambda x: x.__class__.__name__)
            total += len(items[package.ntiid])
            
        result['ItemCount'] = result['Total'] = total
        return result

@view_config(context=IDataserverFolder)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN,
               name='ResetPackagePresentationAssets')
class ResetPackagePresentationAssetsView(AbstractAuthenticatedView,
                                         ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        values = super(ResetPackagePresentationAssetsView, self).readInput(self, value=value)
        return CaseInsensitiveDict(values)

    def __call__(self):
        now = time.time()
        values = self.readInput()
        ntiids = _get_package_ntiids(values)
        if not ntiids:
            packages = list(yield_content_packages(all_packages=True))
        else:
            packages = list(yield_content_packages(ntiids=ntiids))

        total = 0
        result = LocatedExternalDict()
        for package in packages:
            total += len(clear_content_package_assets(package, True))
            
        result['Total'] = total
        result['Elapsed'] = time.time() - now
        return result

@view_config(context=IDataserverFolder)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN,
               name='RemovePackageInaccessibleAssets')
class RemovePackageInaccessibleAssetsView(AbstractAuthenticatedView,
                                          ModeledContentUploadRequestUtilsMixin):

    def _unregister(self, sites_names, provided, name):
        hostsites = component.getUtility(IEtcNamespace, name='hostsites')
        for site_name in sites_names:
            try:
                folder = hostsites[site_name]
                registry = folder.getSiteManager()
                unregisterUtility(registry, provided=provided, name=name)
            except KeyError:
                pass

    def _assets(self, registry):
        for iface in PACKAGE_CONTAINER_INTERFACES:
            for ntiid, asset in list(registry.getUtilitiesFor(iface)):
                yield ntiid, asset

    def __call__(self):
        now = time.time()
        registry = get_registry()
        catalog = get_library_catalog()
        sites = get_component_hierarchy_names()
        intids = component.getUtility(IIntIds)

        result = LocatedExternalDict()
        items = result[ITEMS] = []

        registered = 0
        references = catalog.get_references(sites=sites,
                                            provided=PACKAGE_CONTAINER_INTERFACES)

        for ntiid, asset in self._assets(registry):
            uid = intids.queryId(asset)
            provided = iface_of_thing(asset)
            if uid is None:
                items.append(repr((provided.__name__, ntiid)))
                self._unregister(sites, provided=provided, name=ntiid)
            elif uid not in references:
                items.append(repr((provided.__name__, ntiid, uid)))
                self._unregister(sites, provided=provided, name=ntiid)
                intids.unregister(asset)
            registered += 1

        result['TotalRemoved'] = len(items)
        result['TimeElapsed'] = time.time() - now
        result['TotalRegisteredAssets'] = registered
        result['TotalCatalogedAssets'] = len(references)
        return result

@view_config(context=IDataserverFolder)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN,
               name='RemoveAllPackagesPresentationAssets')
class RemoveAllPackagesPresentationAssetsView(RemovePackageInaccessibleAssetsView):

    def __call__(self):
        now = time.time()
        registry = get_registry()
        catalog = get_library_catalog()
        sites = get_component_hierarchy_names()
        intids = component.getUtility(IIntIds)

        registered = 0
        result = LocatedExternalDict()
        references = catalog.get_references(sites=sites,
                                            provided=PACKAGE_CONTAINER_INTERFACES)
        for uid in references:
            catalog.unindex(uid)
            
        for ntiid, asset in self._assets(registry):
            uid = intids.queryId(asset)
            provided = iface_of_thing(asset)
            self._unregister(sites, provided=provided, name=ntiid)
            if uid is not None:
                intids.unregister(asset)
            registered += 1

        for package in yield_content_packages(all_packages=True):
            clear_package_assets(package)
            clear_namespace_last_modified(package, catalog)

        result['TimeElapsed'] = time.time() - now
        result['TotalRegisteredAssets'] = registered
        result['TotalCatalogedAssets'] = len(references)
        return result
