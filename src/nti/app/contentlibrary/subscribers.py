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

from zope.intid import IIntIds

from ZODB.interfaces import IConnection

from nti.contentlibrary.indexed_data import get_catalog
from nti.contentlibrary.indexed_data import get_registry

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IContentPackageLibraryDidSyncEvent

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

from nti.site.utils import registerUtility
from nti.site.utils import unregisterUtility
from nti.site.interfaces import IHostPolicySiteManager

from .interfaces import IContentBoard

ITEMS = StandardExternalFields.ITEMS

@component.adapter(IContentPackageLibrary, IContentPackageLibraryDidSyncEvent)
def _on_content_pacakge_library_synced(library, event):
	site = library.__parent__
	if IHostPolicySiteManager.providedBy(site):
		bundle_library = site.getUtility(IContentPackageBundleLibrary)
		for bundle in bundle_library.values():
			board = IContentBoard(bundle, None)
			if board is not None:
				board.createDefaultForum()

def prepare_json_text(s):
	result = unicode(s, 'utf-8') if isinstance(s, bytes) else s
	return result

def get_connection(registry=None):
	registry = get_registry(registry)
	result = IConnection(registry, None)
	return result

def intid_register(item, registry, intids=None, connection=None):
	intids = component.queryUtility(IIntIds) if intids is None else intids
	connection = get_connection(registry) if connection is None else connection
	if connection is not None:
		connection.add(item)
		intids.register(item, event=False)
		return True
	return False

def _register_utility(item, provided, ntiid, registry=None, intids=None, connection=None):
	if provided.providedBy(item):
		registry = get_registry(registry)
		registered = registry.queryUtility(provided, name=ntiid)
		if registered is None:
			assert is_valid_ntiid_string(ntiid), "Invalid NTIID %s" % ntiid
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

def _removed_registered(provided, name, intids=None, registry=None, catalog=None):
	registry = get_registry(registry)
	registered = registry.queryUtility(provided, name=name)
	intids = component.queryUtility(IIntIds) if intids is None else intids
	if registered is not None:
		catalog = get_catalog() if catalog is None else catalog
		if catalog is not None: # may be None in test mode
			catalog.unindex(registered, intids=intids)
		unregisterUtility(registry, provided=provided, name=name)
		intids.unregister(registered, event=False)
	return registered

def _remove_from_registry(containers=None, namespace=None, provided=None,
						  registry=None, intids=None, catalog=None):
	"""
	For our type, get our indexed objects so we can remove from both the
	registry and the index.
	"""
	result = []
	registry = get_registry(registry)
	catalog = get_catalog() if catalog is None else catalog
	if catalog is None: # may be None in test mode
		return result
	else:
		intids = component.queryUtility(IIntIds) if intids is None else intids
		for utility in catalog.search_objects(intids=intids, provided=provided,
											  container_ntiids=containers, namespace=namespace):
			try:
				ntiid = utility.ntiid
				if ntiid:
					result.append(utility)
					_removed_registered(provided,
										name=ntiid,
										intids=intids,
										catalog=catalog,
										registry=registry)
			except AttributeError:
				pass
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
	lineage_ntiids = _get_container_tree(container_id)
	lineage_ntiids = None if not lineage_ntiids else lineage_ntiids
	# index item
	catalog.index(item, container_ntiids=lineage_ntiids,
				  namespace=content_package.ntiid)
	# check for slide decks
	if INTISlideDeck.providedBy(item):
		for slide in item.Slides or ():
			result += 1
			catalog.index(slide, container_ntiids=lineage_ntiids,
				  		  namespace=content_package.ntiid)

		for video in item.Videos or ():
			result += 1
			catalog.index(video, container_ntiids=lineage_ntiids,
				  		  namespace=content_package.ntiid)
	return result

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

def _index_items(content_package, index, item_iface, removed, catalog, registry):
	result = 0
	for container_id, indexed_ids in index['Containers'].items():
		for indexed_id in indexed_ids:
			obj = registry.queryUtility(item_iface, name=indexed_id)
			if obj is not None:
				result += _index_item(obj, content_package,
									  container_id, catalog)
	return result

def _update_index_when_content_changes(content_package, index_filename,
									   item_iface, object_creator, catalog=None):
	catalog = get_catalog() if catalog is None else catalog
	sibling_key = content_package.does_sibling_entry_exist(index_filename)
	if not sibling_key:
		# Nothing to do
		return

	if catalog is not None: # may be None in test mode
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
	intids = component.queryUtility(IIntIds)

	removed = _remove_from_registry(namespace=content_package.ntiid,
									provided=item_iface,
									registry=registry,
									catalog=catalog,
									intids=intids)

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
							  			 	 intids=intids))

		removed.extend(_remove_from_registry(namespace=content_package.ntiid,
							  				 provided=INTISlideVideo,
							 				 registry=registry,
							  				 catalog=catalog,
							  				 intids=intids))

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

	# Index our contained items; ignoring the global library.
	index_item_count = 0
	if registry != component.getGlobalSiteManager():
		index_item_count = _index_items(content_package, index, item_iface, 
										removed, catalog, registry)

	logger.info('Finished indexing %s (registered=%s) (indexed=%s) (removed=%s)',
				sibling_key, registered_count, index_item_count, removed_count)

INDICES = ( ('audio_index.json', INTIAudio, create_ntiaudio_from_external),
			('video_index.json', INTIVideo, create_ntivideo_from_external),
			('timeline_index.json', INTITimeline, create_timelime_from_external),
			('slidedeck_index.json', INTISlideDeck, create_object_from_external),
			('related_content_index.json', INTIRelatedWorkRef, create_relatedwork_from_external) )

def _clear_assets(content_package):
	def recur(unit):
		for child in unit.children or ():
			recur(child)
		container = IPresentationAssetContainer(unit, None)
		if container is not None:
			container.clear()
	recur(content_package)

def _update_indices_when_content_changes(content_package, event):
	for name, item_iface, func in INDICES:
		_update_index_when_content_changes(content_package, name, item_iface, func)

def _clear_when_removed(content_package):
	"""
	Because we don't know where the data is stored, when an
	content package is removed we need to clear its data.
	"""
	removed_count = 0
	# Remove indexes for our contained items; ignoring the global library.
	# Not sure if this will work when we have shared items
	# across multiple content packages.
	registry = get_registry()
	if registry != component.getGlobalSiteManager():
		catalog = get_catalog()
		for _, item_iface, _ in INDICES:
			removed = _remove_from_registry(namespace=content_package.ntiid,
								  			provided=item_iface,
								  			catalog=catalog)
			removed_count += len(removed)
		removed = _remove_from_registry(namespace=content_package.ntiid,
							  			provided=INTISlide,
							  			catalog=catalog)
		removed_count += len(removed)

		removed = _remove_from_registry(namespace=content_package.ntiid,
							  			provided=INTISlideVideo,
							 			catalog=catalog)
		removed_count += len(removed)
	logger.info('Removed indexes for content package %s (removed=%s)',
				content_package, removed_count)

def _clear_index_when_content_removed(content_package, event):
	return _clear_when_removed(content_package)
