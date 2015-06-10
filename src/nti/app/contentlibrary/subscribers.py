#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson
import anyjson as json

from zope import component

from zope.intid import IIntIds

from ZODB.interfaces import IConnection

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IGlobalContentPackageLibrary
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IContentPackageLibraryDidSyncEvent

from nti.contenttypes.presentation.interfaces import INTIAudio
from nti.contenttypes.presentation.interfaces import INTIVideo
from nti.contenttypes.presentation.interfaces import INTISlide
from nti.contenttypes.presentation.interfaces import INTITimeline
from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import INTISlideVideo
from nti.contenttypes.presentation.interfaces import INTIRelatedWorkRef

from nti.contenttypes.presentation.utils import create_object_from_external
from nti.contenttypes.presentation.utils import create_ntiaudio_from_external
from nti.contenttypes.presentation.utils import create_ntivideo_from_external
from nti.contenttypes.presentation.utils import create_timelime_from_external
from nti.contenttypes.presentation.utils import create_relatedwork_from_external

from nti.externalization.interfaces import StandardExternalFields

from nti.ntiids.ntiids import is_valid_ntiid_string

from nti.site.utils import registerUtility
from nti.site.interfaces import IHostPolicySiteManager

from nti.contentlibrary.indexed_data import get_catalog
from nti.contentlibrary.indexed_data.interfaces import TAG_NAMESPACE_FILE
from nti.contentlibrary.indexed_data.interfaces import IAudioIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import ITimelineIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import ISlideDeckIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IRelatedContentIndexedDataContainer

from .interfaces import IContentBoard

ITEMS = StandardExternalFields.ITEMS

INTERFACE_TUPLES = (
	(IAudioIndexedDataContainer, INTIAudio, create_ntiaudio_from_external),
	(IVideoIndexedDataContainer, INTIVideo, create_ntivideo_from_external),
	(ITimelineIndexedDataContainer, INTITimeline, create_timelime_from_external),
	(ISlideDeckIndexedDataContainer, INTISlideDeck, create_object_from_external),
	(IRelatedContentIndexedDataContainer, INTIRelatedWorkRef, create_relatedwork_from_external))

@component.adapter(IContentPackageLibrary, IContentPackageLibraryDidSyncEvent)
def _on_content_pacakge_library_synced(library, event):
	site  = library.__parent__
	if IHostPolicySiteManager.providedBy(site):
		bundle_library = site.getUtility(IContentPackageBundleLibrary)
		for bundle in bundle_library.values():
			board = IContentBoard(bundle, None)
			if board is not None:
				board.createDefaultForum()

def prepare_json_text(s):
	result = unicode(s, 'utf-8') if isinstance(s, bytes) else s
	return result

def _registry(registry=None):
	if registry is None:
		library = component.queryUtility(IContentPackageLibrary)
		if IGlobalContentPackageLibrary.providedBy(library):
			registry = component.getGlobalSiteManager()
		else:
			registry = component.getSiteManager()
	return registry

def _connection(registry=None):
	registry = _registry(registry)
	result = IConnection(registry, None)
	return result

def intid_register(item, registry, intids=None, connection=None):
	intids = component.queryUtility(IIntIds) if intids is None else intids
	connection = _connection(registry) if connection is None else connection
	if connection is not None:
		connection.add(item)
		intids.register(item, event=False)
		return True
	return False

def _register_utility(item, provided, ntiid, registry=None, intids=None, connection=None):
	if provided.providedBy(item):
		registry = _registry(registry)
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
	registry = _registry(registry)
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
	registry = _registry(registry)
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

def _get_container_tree( container_id ):
	library = component.queryUtility( IContentPackageLibrary )
	paths = library.pathToNTIID( container_id )
	return [path.ntiid for path in paths] if paths else ()

def _update_index_when_content_changes( content_package, index_iface, item_iface, object_creator, force_change=False ):
	namespace = index_iface.getTaggedValue(TAG_NAMESPACE_FILE)
	sibling_key = content_package.does_sibling_entry_exist(namespace)
	if not sibling_key:
		# Nothing to do
		return

	container = index_iface( content_package )
	if 		not force_change \
		and container.lastModified \
		and container.lastModified >= sibling_key.lastModified:
		logger.info("No change to %s since %s, ignoring",
					sibling_key,
					sibling_key.lastModified )
		return
	container.lastModified = sibling_key.lastModified

	logger.info( "Loading index data %s", sibling_key )
	index_text = content_package.read_contents_of_sibling_entry( namespace )

	if isinstance(index_text, bytes):
		index_text = index_text.decode('utf-8')

	index = json.loads(index_text)
	registry = _registry()
	connection = _connection( registry )
	catalog = get_catalog()

	# These are structured as follows:
	# {
	#   Items: { ntiid-of_item: data }
	#   Containers: { ntiid-of-content-unit: [list-of-ntiid-of-item ] }
	# }

	# Load our json index files
	if item_iface == INTISlideDeck:
		_load_and_register_slidedeck_json(	index_text,
											registry=registry,
										   	connection=connection,
										   	object_creator=object_creator)
	elif object_creator is not None:
		_load_and_register_json( item_iface, index_text,
								registry=registry,
								connection=connection,
								external_object_creator=object_creator)

	# Index our contained items; ignoring the global library.
	if registry != component.getGlobalSiteManager():
		for container_id, indexed_ids in index['Containers'].items():
			for indexed_id in indexed_ids:
				obj = registry.queryUtility( item_iface, name=indexed_id )
				lineage_ntiids = _get_container_tree( container_id )
				if lineage_ntiids:
					catalog.index( obj, container_ntiids=lineage_ntiids )

def _update_audio_index_when_content_changes(content_package, event):
	return _update_index_when_content_changes(content_package,
											  IAudioIndexedDataContainer,
											  INTIAudio,
											  create_ntiaudio_from_external)

def _update_video_index_when_content_changes(content_package, event):
	return _update_index_when_content_changes(content_package,
											  IVideoIndexedDataContainer,
											  INTIVideo,
											  create_ntivideo_from_external)

def _update_related_content_index_when_content_changes(content_package, event):
	return _update_index_when_content_changes(content_package,
											  IRelatedContentIndexedDataContainer,
											  INTIRelatedWorkRef,
											  create_relatedwork_from_external)

def _update_timeline_index_when_content_changes(content_package, event):
	return _update_index_when_content_changes(content_package,
											  ITimelineIndexedDataContainer,
											  INTITimeline,
											  create_timelime_from_external)

def _update_slidedeck_index_when_content_changes(content_package, event):
	return _update_index_when_content_changes(content_package,
											  ISlideDeckIndexedDataContainer,
											  INTISlideDeck,
											  create_object_from_external)

def _clear_when_removed(content_package):
	"""
	Because we don't know where the data is stored, when an
	content package is removed we need to clear its data.
	"""
	# Remove indexes for our contained items; ignoring the global library.
	# Not sure if this will work when we have shared items
	# across multiple content packages.
	registry = _registry()
	if registry != component.getGlobalSiteManager():
		catalog = get_catalog()
		contained_objects = catalog.search_objects( container_ntiids=content_package.ntiid )
		for contained_object in tuple( contained_objects ):
			catalog.unindex( contained_object )

def _clear_audio_index_when_content_removed(content_package, event):
	return _clear_when_removed(content_package)

def _clear_video_index_when_content_removed(content_package, event):
	return _clear_when_removed(content_package)

def _clear_related_index_when_content_removed(content_package, event):
	return _clear_when_removed(content_package)

def _clear_timeline_index_when_content_removed(content_package, event):
	return _clear_when_removed(content_package)

def _clear_slidedeck_index_when_content_removed(content_package, event):
	return _clear_when_removed(content_package)

