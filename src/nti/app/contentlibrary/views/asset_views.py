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
from collections import defaultdict

from zope import component

from zope.component.hooks import site as current_site

from zope.intid import IIntIds

from zope.security.management import endInteraction
from zope.security.management import restoreInteraction

from zope.traversing.interfaces import IEtcNamespace

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
from nti.contenttypes.presentation.interfaces import IPresentationAsset
from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.recorder.record import remove_transaction_history

from nti.site.utils import unregisterUtility
from nti.site.interfaces import IHostPolicyFolder
from nti.site.site import get_site_for_site_names
from nti.site.site import get_component_hierarchy_names

from nti.traversal.traversal import find_interface

from ..utils import yield_content_packages

from ..subscribers import update_indices_when_content_changes

from . import iface_of_thing

ITEMS = StandardExternalFields.ITEMS
NTIID = StandardExternalFields.NTIID
MIMETYPE = StandardExternalFields.MIMETYPE

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
			   name='RemovePackageInaccessibleAssets')
class RemovePackageInaccessibleAssetsView(AbstractAuthenticatedView,
										  ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		return _read_input(self.request)

	def _reverse(self, site_names):
		sites_names = list(site_names)
		sites_names.reverse()
		return site_names

	def _component_registry(self, site_names, asset, provided, name):
		hostsites = component.getUtility(IEtcNamespace, name='hostsites')
		for site_name in self._reverse(site_names):  # higher sites first
			try:
				folder = hostsites[site_name]
				registry = folder.getSiteManager()
				if registry.queryUtility(provided, name=name) == asset:
					return registry
			except KeyError:
				pass
		return None

	def _unregister(self, site_names, asset, provided, name):
		registry = self._component_registry(site_names, asset, provided, name)
		if registry is not None:
			result = unregisterUtility(registry,
									   provided=provided,
									   name=name)
		else:
			registry = False
		return result

	def _registered_assets(self, registry):
		for iface in PACKAGE_CONTAINER_INTERFACES:
			for ntiid, asset in list(registry.getUtilitiesFor(iface)):
				yield ntiid, asset

	def _contained_assets(self):
		result = defaultdict(list)
		containers = defaultdict(list)
		def recur(unit):
			for child in unit.children or ():
				recur(child)
			container = IPresentationAssetContainer(unit)
			for key, value in container.items():
				provided = iface_of_thing(value)
				if provided in PACKAGE_CONTAINER_INTERFACES:
					result[key].append(value)
					containers[key].append(container)
		for pacakge in yield_content_packages():
			recur(pacakge)
		return result, containers

	def _pop(self, container, ntiid):
		if ntiid in container:
			del container[ntiid]

	def _do_call(self, result):
		registry = get_registry()
		catalog = get_library_catalog()
		intids = component.getUtility(IIntIds)
		sites = get_component_hierarchy_names()

		contained = 0
		registered = 0
		items = result[ITEMS] = []
		master, storages = self._contained_assets()

		# clean containers by removing those assets that either
		# don't have an intid or cannot be found in the registry
		for ntiid, assets in list(master.items()):  # mutating
			provided = None
			containers = storages[ntiid]
			# check every object in the storage containers to look for
			# invalid objects
			for idx, asset in enumerate(assets):
				uid = intids.queryId(asset)
				provided = iface_of_thing(asset)
				if uid is None:
					self._pop(containers[idx], ntiid)
					remove_transaction_history(asset)

			# check registration
			if component.queryUtility(provided, name=ntiid) is None:
				# unindex and remove from containers
				for idx, asset in enumerate(assets):
					uid = intids.queryId(asset)
					if uid is not None:
						catalog.unindex(uid)
						intids.unregister(asset)
					self._pop(containers[idx], ntiid)
					remove_transaction_history(asset)
				# update master list
				master.pop(ntiid, None)
				storages.pop(ntiid, None)
			else:
				contained += 1

		# unregister those utilities that cannot be found
		# in the course containers
		for ntiid, asset in self._registered_assets(registry):
			uid = intids.queryId(asset)
			provided = iface_of_thing(asset)
			if uid is None or ntiid not in master:
				remove_transaction_history(asset)
				self._unregister(sites, asset, provided=provided, name=ntiid)
				if uid is not None:
					catalog.unindex(uid)
					intids.unregister(asset)
				items.append({
					'IntId':uid,
					NTIID:ntiid,
					MIMETYPE:asset.mimeType,
				})
			else:
				registered += 1

		# unindex invalid entries in catalog
		references = catalog.get_references(sites=sites,
										 	provided=PACKAGE_CONTAINER_INTERFACES)
		for uid in references or ():
			asset = intids.queryObject(uid)
			if asset is None or not IPresentationAsset.providedBy(asset):
				catalog.unindex(uid)
			else:
				ntiid = asset.ntiid
				provided = iface_of_thing(asset)
				if component.queryUtility(provided, name=ntiid) is None:
					catalog.unindex(uid)
					intids.unregister(asset)
					remove_transaction_history(asset)
					items.append({
						'IntId':uid,
						NTIID:ntiid,
						MIMETYPE:asset.mimeType,
					})

		items.sort(key=lambda x:x[NTIID])
		result['TotalContainedAssets'] = contained
		result['TotalRegisteredAssets'] = registered
		result['Total'] = result['ItemCount'] = len(items)
		return result

	def __call__(self):
		result = LocatedExternalDict()
		endInteraction()
		try:
			self._do_call(result)
		finally:
			restoreInteraction()
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
		items = result[ITEMS] = []
		ntiids = _get_package_ntiids(values)
		for package in yield_content_packages(ntiids):
			folder = find_interface(package, IHostPolicyFolder, strict=False)
			with current_site(get_site_for_site_names((folder.__name__,))):
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
