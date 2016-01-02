#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson

from zope import component

from zope.component.hooks import getSite

from zope.intid import IIntIds

from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from ZODB.interfaces import IConnection

from nti.coremetadata.interfaces import IRecordable

from nti.contentlibrary.indexed_data import get_registry
from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IGlobalContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IContentPackageSyncResults
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IContentPackageLibraryDidSyncEvent

from nti.contentlibrary.synchronize import ContentPackageSyncResults

from nti.contenttypes.presentation import iface_of_asset

from nti.contenttypes.presentation.interfaces import INTIAudio
from nti.contenttypes.presentation.interfaces import INTIVideo
from nti.contenttypes.presentation.interfaces import INTISlide
from nti.contenttypes.presentation.interfaces import INTITimeline
from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import INTISlideVideo
from nti.contenttypes.presentation.interfaces import INTIRelatedWorkRef
from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.contenttypes.presentation.utils import create_object_from_external
from nti.contenttypes.presentation.utils import create_ntiaudio_from_external
from nti.contenttypes.presentation.utils import create_ntivideo_from_external
from nti.contenttypes.presentation.utils import create_timelime_from_external
from nti.contenttypes.presentation.utils import create_relatedwork_from_external

from nti.externalization.interfaces import StandardExternalFields

from nti.ntiids.ntiids import is_valid_ntiid_string

from nti.recorder.record import copy_transaction_history
from nti.recorder.record import remove_transaction_history

from nti.site.utils import registerUtility
from nti.site.utils import unregisterUtility
from nti.site.interfaces import IHostPolicySiteManager
from nti.site.site import get_component_hierarchy_names

from .interfaces import IContentBoard

ITEMS = StandardExternalFields.ITEMS

INDICES = ( ('audio_index.json', INTIAudio, create_ntiaudio_from_external),
			('video_index.json', INTIVideo, create_ntivideo_from_external),
			('timeline_index.json', INTITimeline, create_timelime_from_external),
			('slidedeck_index.json', INTISlideDeck, create_object_from_external),
			('related_content_index.json', INTIRelatedWorkRef, create_relatedwork_from_external))

def prepare_json_text(s):
	result = unicode(s, 'utf-8') if isinstance(s, bytes) else s
	return result

def get_connection(registry=None):
	registry = get_registry(registry)
	if registry == component.getGlobalSiteManager():
		return None
	else:
		result = IConnection(registry, None)
		return result

def intid_register(item, registry, intids=None, connection=None):
	intids = component.getUtility(IIntIds) if intids is None else intids
	connection = get_connection(registry) if connection is None else connection
	if connection is not None:
		connection.add(item)
		intids.register(item, event=True)
		return True
	return False

def _register_utility(item, provided, ntiid, registry=None, intids=None, connection=None):
	intids = component.getUtility(IIntIds) if intids is None else intids
	if provided.providedBy(item):
		registry = get_registry(registry)
		registered = registry.queryUtility(provided, name=ntiid)
		if registered is None or intids.queryId(registered) is None:
			assert is_valid_ntiid_string(ntiid), "Invalid NTIID %s" % ntiid
			if intids.queryId(registered) is None:  # remove if invalid
				unregisterUtility(registry, provided=provided, name=ntiid)
			registerUtility(registry, item, provided=provided, name=ntiid)
			intid_register(item, registry, intids, connection)
			return (True, item)
		return (False, registered)
	return (False, None)

def _was_utility_registered(item, item_iface, ntiid, registry=None,
							connection=None, intids=None,):
	result, _ = _register_utility(item, item_iface, ntiid,
								  registry=registry,
								  intids=intids,
								  connection=connection)
	return result

def _load_and_register_items(item_iterface, items, registry=None, connection=None,
							 external_object_creator=create_object_from_external):
	result = []
	registry = get_registry(registry)
	for ntiid, data in items.items():
		internal = external_object_creator(data, notify=False)
		if _was_utility_registered(internal, item_iterface, ntiid,
								   registry=registry, connection=connection):
			result.append(internal)
	return result

def _load_and_register_json(item_iterface, jtext, registry=None, connection=None,
							external_object_creator=create_object_from_external):
	index = simplejson.loads(prepare_json_text(jtext))
	items = index.get(ITEMS) or {}
	result = _load_and_register_items(item_iterface, items,
									  registry=registry,
									  connection=connection,
									  external_object_creator=external_object_creator)
	return result

def _canonicalize(items, item_iface, registry):
	recorded = []
	for idx, item in enumerate(items or ()):
		ntiid = item.ntiid
		result, registered = _register_utility(item, item_iface, ntiid, registry)
		if result:
			recorded.append(item)
		else:
			items[idx] = registered  # replaced w/ registered
	return recorded

def _load_and_register_slidedeck_json(jtext, registry=None, connection=None,
									  object_creator=create_object_from_external):
	result = []
	registry = get_registry(registry)
	index = simplejson.loads(prepare_json_text(jtext))
	items = index.get(ITEMS) or {}
	for ntiid, data in items.items():
		internal = object_creator(data, notify=False)
		if 	INTISlide.providedBy(internal) and \
			_was_utility_registered(internal, INTISlide, ntiid, registry, connection):
			result.append(internal)
		elif INTISlideVideo.providedBy(internal) and \
			 _was_utility_registered(internal, INTISlideVideo, ntiid, registry, connection):
			result.append(internal)
		elif INTISlideDeck.providedBy(internal):
			result.extend(_canonicalize(internal.Slides, INTISlide, registry))
			result.extend(_canonicalize(internal.Videos, INTISlideVideo, registry))
			if _was_utility_registered(internal, INTISlideDeck, ntiid, registry, connection):
				result.append(internal)
	return result

def _can_be_removed(registered, force=False):
	result = registered is not None and \
			 (force or not IRecordable.providedBy(registered) or not registered.locked)
	return result
can_be_removed = _can_be_removed

def _removed_registered(provided, name, intids=None, registry=None,
						catalog=None, force=False):
	registry = get_registry(registry)
	registered = registry.queryUtility(provided, name=name)
	intids = component.getUtility(IIntIds) if intids is None else intids
	if _can_be_removed(registered, force=force):
		catalog = get_library_catalog() if catalog is None else catalog
		catalog.unindex(registered, intids=intids)
		if not unregisterUtility(registry, provided=provided, name=name):
			logger.warn("Could not unregister (%s,%s) during sync, continuing...",
						provided.__name__, name)
		intids.unregister(registered, event=False)
	elif registered is not None:
		logger.warn("Object (%s,%s) is locked cannot be removed during sync",
					provided.__name__, name)
		registered = None  # set to None since it was not removed
	return registered

def _remove_from_registry(containers=None,
						  namespace=None,
						  provided=None,
						  registry=None,
						  intids=None,
						  catalog=None,
						  force=False,
						  sync_results=None):
	"""
	For our type, get our indexed objects so we can remove from both the
	registry and the index.
	"""
	result = []
	registry = get_registry(registry)
	catalog = get_library_catalog() if catalog is None else catalog
	if catalog is None:  # may be None in test mode
		return result
	else:
		sites = get_component_hierarchy_names()
		intids = component.getUtility(IIntIds) if intids is None else intids
		for item in catalog.search_objects(intids=intids, provided=provided,
										   container_ntiids=containers,
										   namespace=namespace,
										   sites=sites):
			ntiid = item.ntiid
			removed = _removed_registered(provided,
										  name=ntiid,
										  force=force,
										  intids=intids,
										  catalog=catalog,
										  registry=registry)
			if removed is not None:
				result.append(removed)
			elif sync_results is not None:
				sync_results.add(ntiid, locked=True)
	return result

def _get_container_tree(container_id):
	library = component.queryUtility(IContentPackageLibrary)
	paths = library.pathToNTIID(container_id)
	results = {path.ntiid for path in paths} if paths else ()
	return results

def _get_file_last_mod_namespace(unit, filename):
	return '%s.%s.LastModified' % (unit.ntiid, filename)

def _index_item(item, content_package, container_id, catalog):
	result = 1
	sites = get_component_hierarchy_names()
	lineage_ntiids = _get_container_tree(container_id)
	lineage_ntiids = None if not lineage_ntiids else lineage_ntiids
	# index item
	catalog.index(item, container_ntiids=lineage_ntiids,
				  namespace=content_package.ntiid, sites=sites)
	# check for slide decks
	if INTISlideDeck.providedBy(item):
		extended = tuple(lineage_ntiids or ()) + (item.ntiid,)
		for slide in item.Slides or ():
			result += 1
			catalog.index(slide, container_ntiids=extended,
				  		  namespace=content_package.ntiid, sites=sites)

		for video in item.Videos or ():
			result += 1
			catalog.index(video, container_ntiids=extended,
				  		  namespace=content_package.ntiid, sites=sites)
	return result

def _copy_remove_transactions(items, registry=None):
	registry = get_registry(registry)
	for item in items or ():
		provided = iface_of_asset(item)
		obj = registry.queryUtility(provided, name=item.ntiid)
		if obj is None:
			remove_transaction_history(item)
		else:
			copy_transaction_history(item, obj)

def _store_asset(content_package, container_id, ntiid, item):
	try:
		unit = content_package[container_id]
	except KeyError:
		unit = content_package

	container = IPresentationAssetContainer(unit, None)
	if container is not None:
		container[ntiid] = item
		# check for slide decks
		if INTISlideDeck.providedBy(item):
			for slide in item.Slides or ():
				container[slide.ntiid] = slide

			for video in item.Videos or ():
				container[video.ntiid] = video
		return True
	return False

def _index_items(content_package, index, item_iface, catalog, registry):
	result = 0
	for container_id, indexed_ids in index['Containers'].items():
		for indexed_id in indexed_ids:
			obj = registry.queryUtility(item_iface, name=indexed_id)
			if obj is not None:
				_store_asset(content_package, container_id, indexed_id, obj)
				result += _index_item(obj, content_package,
									  container_id, catalog)
	return result

def _update_index_when_content_changes(content_package,
									   index_filename,
									   item_iface,
									   object_creator,
									   catalog=None,
									   sync_results=None):
	catalog = get_library_catalog() if catalog is None else catalog
	sibling_key = content_package.does_sibling_entry_exist(index_filename)
	if not sibling_key:
		# Nothing to do
		return

	if sync_results is None:
		sync_results = _new_sync_results(content_package)

	if catalog is not None:  # may be None in test mode
		sk_lastModified = sibling_key.lastModified
		last_mod_namespace = _get_file_last_mod_namespace(content_package, index_filename)
		last_modified = catalog.get_last_modified(last_mod_namespace)
		if last_modified and last_modified >= sk_lastModified:
			logger.info("No change to %s since %s, ignoring",
						sibling_key,
						sk_lastModified)
			return
		catalog.set_last_modified(last_mod_namespace, sk_lastModified)

	index_text = content_package.read_contents_of_sibling_entry(index_filename)

	if isinstance(index_text, bytes):
		index_text = index_text.decode('utf-8')

	index = simplejson.loads(index_text)
	registry = get_registry()
	connection = get_connection(registry)
	intids = component.getUtility(IIntIds)

	removed = _remove_from_registry(namespace=content_package.ntiid,
									provided=item_iface,
									registry=registry,
									catalog=catalog,
									intids=intids,
									sync_results=sync_results)

	# These are structured as follows:
	# {
	#   Items: { ntiid-of_item: data }
	#   Containers: { ntiid-of-content-unit: [list-of-ntiid-of-item ] }
	# }

	# Load our json index files
	# TODO Do we need to register our global, non-persistent catalog?
	added = ()
	if item_iface == INTISlideDeck:
		# Also remove our other slide types
		removed.extend(_remove_from_registry(namespace=content_package.ntiid,
							  				 provided=INTISlide,
							  				 registry=registry,
							 				 catalog=catalog,
							  			 	 intids=intids,
							  			 	 sync_results=sync_results))

		removed.extend(_remove_from_registry(namespace=content_package.ntiid,
							  				 provided=INTISlideVideo,
							 				 registry=registry,
							  				 catalog=catalog,
							  				 intids=intids,
							  				 sync_results=sync_results))

		added = _load_and_register_slidedeck_json(index_text,
										  		  registry=registry,
										  		  connection=connection,
										 		  object_creator=object_creator)
	elif object_creator is not None:
		added = _load_and_register_json(item_iface, index_text,
										registry=registry,
										connection=connection,
										external_object_creator=object_creator)
	registered_count = len(added)
	removed_count = len(removed)

	# keep transaction history
	_copy_remove_transactions(removed, registry=registry)

	# update sync results
	for item in added or ():
		sync_results.add(item, locked=False)

	# Index our contained items; ignoring the global library.
	index_item_count = 0
	if registry != component.getGlobalSiteManager():
		index_item_count = _index_items(content_package, index, item_iface,
										catalog, registry)

	logger.info('Finished indexing %s (registered=%s) (indexed=%s) (removed=%s)',
				sibling_key, registered_count, index_item_count, removed_count)

def _clear_assets(content_package, force=False):
	def recur(unit):
		for child in unit.children or ():
			recur(child)
		container = IPresentationAssetContainer(unit)
		if force:
			container.clear()
		else:
			for key, value in list(container.items()):  # mutating
				if can_be_removed(value, force):
					del container[key]

	recur(content_package)
clear_package_assets = _clear_assets

def _clear_last_modified(content_package, catalog=None):
	catalog = get_library_catalog() if catalog is None else catalog
	for name, _, _ in INDICES:
		namespace = _get_file_last_mod_namespace(content_package, name)
		catalog.remove_last_modified(namespace)
clear_namespace_last_modified = _clear_last_modified

# update events

def _new_sync_results(content_package):
	result = ContentPackageSyncResults(Site=getattr(getSite(), '__name__', None),
									   ContentPackageNTIID=content_package.ntiid)
	return result

def _get_sync_results(content_package, event):
	all_results = getattr(event, "results", None)
	if not all_results or not IContentPackageSyncResults.providedBy(all_results[-1]):
		result = _new_sync_results(content_package)
		if all_results is not None:
			all_results.append(result)
		return result
	else:
		return all_results[-1]

def update_indices_when_content_changes(content_package, sync_results=None):
	if sync_results is None:
		sync_results = _new_sync_results(content_package)
	_clear_assets(content_package)
	for name, item_iface, func in INDICES:
		_update_index_when_content_changes(content_package,
										   index_filename=name,
										   object_creator=func,
										   item_iface=item_iface,
										   sync_results=sync_results)
	return sync_results

@component.adapter(IContentPackage, IObjectModifiedEvent)
def _update_indices_when_content_changes(content_package, event):
	sync_results = _get_sync_results(content_package, event)
	update_indices_when_content_changes(content_package, sync_results)

# clear events

def _clear_when_removed(content_package, force=True, process_global=False):
	"""
	Because we don't know where the data is stored, when an
	content package is removed we need to clear its data.
	"""
	result = []
	catalog = get_library_catalog()
	_clear_assets(content_package, force)

	# Remove indexes for our contained items; ignoring the global library.
	# Not sure if this will work when we have shared items
	# across multiple content packages.
	if not process_global and IGlobalContentPackage.providedBy(content_package):
		return result
	_clear_last_modified(content_package, catalog)

	for _, item_iface, _ in INDICES:
		removed = _remove_from_registry(namespace=content_package.ntiid,
							  			provided=item_iface,
							  			catalog=catalog,
							  			force=force)
		result.extend(removed)
	removed = _remove_from_registry(namespace=content_package.ntiid,
						  			provided=INTISlide,
						  			catalog=catalog,
						  			force=force)
	result.extend(removed)

	removed = _remove_from_registry(namespace=content_package.ntiid,
						  			provided=INTISlideVideo,
						 			catalog=catalog,
						 			force=force)
	result.extend(removed)

	for item in result:
		remove_transaction_history(item)

	logger.info('Removed indexes for content package %s (removed=%s)',
				content_package, len(result))
	return result
clear_content_package_assets = _clear_when_removed

@component.adapter(IContentPackage, IObjectRemovedEvent)
def _clear_index_when_content_removed(content_package, event):
	return _clear_when_removed(content_package)

# forum events

@component.adapter(IContentPackageLibrary, IContentPackageLibraryDidSyncEvent)
def _on_content_pacakge_library_synced(library, event):
	site = library.__parent__
	if IHostPolicySiteManager.providedBy(site):
		bundle_library = site.getUtility(IContentPackageBundleLibrary)
		for bundle in bundle_library.values():
			board = IContentBoard(bundle, None)
			if board is not None:
				board.createDefaultForum()
