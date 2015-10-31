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

from zope.security.management import endInteraction
from zope.security.management import restoreInteraction

from zope.traversing.interfaces import IEtcNamespace

from zope.intid import IIntIds

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.internalization import read_body_as_external_object
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.string import TRUE_VALUES
from nti.common.maps import CaseInsensitiveDict

from nti.contentlibrary.indexed_data import get_registry
from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contenttypes.presentation import PACKAGE_CONTAINER_INTERFACES
from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.recorder.record import remove_transaction_history

from nti.site.utils import unregisterUtility
from nti.site.site import get_component_hierarchy_names

from ..utils import yield_content_packages

from ..subscribers import can_be_removed
from ..subscribers import clear_package_assets
from ..subscribers import clear_content_package_assets
from ..subscribers import clear_namespace_last_modified
from ..subscribers import update_indices_when_content_changes

from . import iface_of_thing

ITEMS = StandardExternalFields.ITEMS

def _get_package_ntiids(values):
	ntiids = values.get('ntiid') or values.get('ntiids')
	if ntiids and isinstance(ntiids, six.string_types):
		ntiids = ntiids.split()
	return ntiids

def _is_true(v):
	return v and str(v).lower() in TRUE_VALUES

def _read_input(request):
	result = CaseInsensitiveDict()
	if request:
		if request.body:
			values = read_body_as_external_object(request)
		else:
			values = request.params
		result.update(values)
	return result

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
			   permission=nauth.ACT_NTI_ADMIN,
			   name='ResetPackagePresentationAssets')
class ResetPackagePresentationAssetsView(AbstractAuthenticatedView,
										 ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		return _read_input(self.request)

	def _do_call(self, result):
		total = 0
		values = self.readInput()
		ntiids = _get_package_ntiids(values)
		force = _is_true(values.get('force'))
		packages = list(yield_content_packages(ntiids))

		result = LocatedExternalDict()
		for package in packages:
			total += len(clear_content_package_assets(package, force=force))
		result['Total'] = total
		return result

	def __call__(self):
		now = time.time()
		result = LocatedExternalDict()
		endInteraction()
		try:
			self._do_call(result)
		finally:
			restoreInteraction()
			result['TimeElapsed'] = time.time() - now
		return result

@view_config(context=IDataserverFolder)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_NTI_ADMIN,
			   name='RemovePackageInaccessibleAssets')
class RemovePackageInaccessibleAssetsView(AbstractAuthenticatedView,
										  ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		return _read_input(self.request)

	def _unregister(self, sites_names, provided, name):
		result = False
		sites_names = list(sites_names)
		sites_names.reverse()
		hostsites = component.getUtility(IEtcNamespace, name='hostsites')
		for site_name in sites_names:
			try:
				folder = hostsites[site_name]
				registry = folder.getSiteManager()
				result = unregisterUtility(registry,
										   provided=provided,
										   name=name) or result
			except KeyError:
				pass
		return result

	def _registered_assets(self, registry):
		for iface in PACKAGE_CONTAINER_INTERFACES:
			for ntiid, asset in list(registry.getUtilitiesFor(iface)):
				yield ntiid, asset

	def _contained_assets(self):
		result = []
		def recur(unit):
			for child in unit.children or ():
				recur(child)
			container = IPresentationAssetContainer(unit, None) or {}
			for key, value in container.items():
				provided = iface_of_thing(value)
				if provided in PACKAGE_CONTAINER_INTERFACES:
					result.append((container, key, value))
		for pacakge in yield_content_packages():
			recur(pacakge)
		return result

	def _do_call(self, result):
		registry = get_registry()
		catalog = get_library_catalog()
		sites = get_component_hierarchy_names()
		intids = component.getUtility(IIntIds)

		registered = 0
		items = result[ITEMS] = []
		references = catalog.get_references(sites=sites,
											provided=PACKAGE_CONTAINER_INTERFACES)

		for ntiid, asset in self._registered_assets(registry):
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

		contained = set()
		for container, ntiid, asset in self._contained_assets():
			uid = intids.queryId(asset)
			provided = iface_of_thing(asset)
			if 	uid is None or uid not in references or \
				component.queryUtility(provided, name=ntiid) is None:
				container.pop(ntiid, None)
				self._unregister(sites, provided=provided, name=ntiid)
				if uid is not None:
					catalog.unindex(uid)
					intids.unregister(asset)
				remove_transaction_history(asset)
			contained.add(ntiid)

		result['TotalRemoved'] = len(items)
		result['TotalRegisteredAssets'] = registered
		result['TotalContainedAssets'] = len(contained)
		result['TotalCatalogedAssets'] = len(references)
		return result

	def __call__(self):
		now = time.time()
		result = LocatedExternalDict()
		endInteraction()
		try:
			self._do_call(result)
		finally:
			restoreInteraction()
			result['TimeElapsed'] = time.time() - now
		return result

@view_config(context=IDataserverFolder)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_NTI_ADMIN,
			   name='RemoveAllPackagesPresentationAssets')
class RemoveAllPackagesPresentationAssetsView(RemovePackageInaccessibleAssetsView):

	def _do_call(self, result):
		values = self.readInput()
		registry = get_registry()
		catalog = get_library_catalog()
		force = _is_true(values.get('force'))
		sites = get_component_hierarchy_names()
		intids = component.getUtility(IIntIds)

		registered = 0
		references = set()
		result_set = catalog.search_objects(sites=sites,
											provided=PACKAGE_CONTAINER_INTERFACES)
		for uid, asset in result_set.iter_pairs():
			if can_be_removed(asset, force=force):
				catalog.unindex(uid)
				references.add(uid)

		for ntiid, asset in self._registered_assets(registry):
			if not can_be_removed(asset, force=force):
				continue
			# remove trax
			remove_transaction_history(asset)
			# unregister utility
			provided = iface_of_thing(asset)
			self._unregister(sites, provided=provided, name=ntiid)
			# unregister fron intid
			uid = intids.queryId(asset)
			if uid is not None:
				intids.unregister(asset)
			# ground if possible
			if hasattr('asset', '__parent__'):
				asset.__parent__ = None
			registered += 1

		for package in yield_content_packages():
			clear_package_assets(package)
			clear_namespace_last_modified(package, catalog)

		result['TotalRegisteredAssets'] = registered
		result['TotalCatalogedAssets'] = len(references)
		return result

	def __call__(self):
		now = time.time()
		result = LocatedExternalDict()
		endInteraction()
		try:
			self._do_call(result)
		finally:
			restoreInteraction()
			result['TimeElapsed'] = time.time() - now
		return result

@view_config(context=IDataserverFolder)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_NTI_ADMIN,
			   name='SyncPackagePresentationAssets')
class SyncPackagePresentationAssetsView(AbstractAuthenticatedView,
										ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		return _read_input(self.request)

	def _do_call(self, result):
		values = self.readInput()
		ntiids = _get_package_ntiids(values)
		packages = list(yield_content_packages(ntiids))
		items = result[ITEMS] = []
		for package in packages:
			items.append(package.ntiid)
			update_indices_when_content_changes(package)
		return result

	def __call__(self):
		now = time.time()
		result = LocatedExternalDict()
		endInteraction()
		try:
			self._do_call(result)
		finally:
			restoreInteraction()
			result['TimeElapsed'] = time.time() - now
		return result
