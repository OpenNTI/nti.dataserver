#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface

from zope.location.interfaces import IContained

from zope.security.interfaces import IPrincipal

from persistent.mapping import PersistentMapping

from BTrees.OOBTree import OOBTree

from pyramid.location import lineage

from nti.appserver.context_providers import get_top_level_contexts

from nti.appserver.interfaces import IJoinableContextProvider
from nti.appserver.interfaces import ForbiddenContextException
from nti.appserver.interfaces import IHierarchicalContextProvider
from nti.appserver.interfaces import ITopLevelContainerContextProvider

from nti.appserver.pyramid_authorization import is_readable

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary

from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contentlibrary.indexed_data.interfaces import INTIIDAdapter
from nti.contentlibrary.indexed_data.interfaces import INamespaceAdapter
from nti.contentlibrary.indexed_data.interfaces import ISlideDeckAdapter
from nti.contentlibrary.indexed_data.interfaces import IContainersAdapter
from nti.contentlibrary.indexed_data.interfaces import IContainedTypeAdapter

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseOutlineNode
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.contenttypes.presentation import iface_of_asset

from nti.contenttypes.presentation.interfaces import INTISlide, INTISlideDeck
from nti.contenttypes.presentation.interfaces import INTISlideVideo
from nti.contenttypes.presentation.interfaces import IPresentationAsset
from nti.contenttypes.presentation.interfaces import ICoursePresentationAsset
from nti.contenttypes.presentation.interfaces import IPackagePresentationAsset
from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.contenttypes.courses.utils import get_course_subinstances
from nti.contenttypes.courses.utils import get_courses_for_packages

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IForum

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import system_user

from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin
from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.site.interfaces import IHostPolicyFolder

from nti.traversal.traversal import find_interface

# Type

class _Type(object):

	__slots__ = (b'type',)

	def __init__(self, type_):
		self.type = type_

@component.adapter(IPresentationAsset)
@interface.implementer(IContainedTypeAdapter)
def _asset_to_contained_type(context):
	provided = iface_of_asset(context)
	return _Type(provided.__name__)

# Namespace

class _Namespace(object):

	__slots__ = (b'namespace',)

	def __init__(self, namespace):
		self.namespace = namespace

@interface.implementer(INamespaceAdapter)
@component.adapter(ICoursePresentationAsset)
def _course_asset_to_namespace(context):
	node = find_interface(context, ICourseOutlineNode, strict=False)
	source = getattr(node, 'src', None)
	if source:
		return _Namespace(source)
	return None

def _package_lineage_to_namespace(context):
	package = find_interface(context, IContentPackage, strict=False)
	if package is not None:
		return _Namespace(package.ntiid)
	return None

@interface.implementer(INamespaceAdapter)
@component.adapter(IPackagePresentationAsset)
def _package_asset_to_namespace(context):
	return _package_lineage_to_namespace(context)

# Namespace

class _NTIID(object):

	__slots__ = (b'ntiid',)

	def __init__(self, ntiid):
		self.ntiid = ntiid

@interface.implementer(INTIIDAdapter)
@component.adapter(IPresentationAsset)
def _asset_to_ntiid(context):
	return _NTIID(context.ntiid)

# Containers

class _Containers(object):

	__slots__ = (b'containers',)

	def __init__(self, containers):
		self.containers = containers

def _package_lineage_to_containers(context):
	result = set()
	for location in lineage(context):
		if IContentUnit.providedBy(location):
			result.add(location.ntiid)
		if IContentPackage.providedBy(location):
			break
	result.discard(None)
	return _Containers(tuple(result))

@interface.implementer(IContainersAdapter)
@component.adapter(IPackagePresentationAsset)
def _pacakge_asset_to_containers(context):
	result = _package_lineage_to_containers(context)
	package = find_interface(context, IContentPackage, strict=False)
	folder = find_interface(context, IHostPolicyFolder, strict=False)
	if package is not None and folder is not None:
		containers = set(result.containers)
		courses = get_courses_for_packages(folder.__name__, package.ntiid)
		for course in courses:
			entry = ICourseCatalogEntry(course)
			containers.add(entry.ntiid)
		result = _Containers(tuple(containers))
	
	# check for slides and slidevideos
	if		(INTISlide.providedBy(context) or INTISlideVideo.providedBy(context)) \
		and context.__parent__ is not None \
		and context.__parent__.ntiid:
		containers = set(result.containers)
		containers.add(context.__parent__.ntiid)
		result = _Containers(tuple(containers))
	return result

@interface.implementer(IContainersAdapter)
@component.adapter(ICoursePresentationAsset)
def _course_asset_to_containers(context):
	course = None
	result = set()
	for location in lineage(context):
		if IPresentationAsset.providedBy(location):
			result.add(location.ntiid)
		if ICourseInstance.providedBy(location):
			course = location
			entry = ICourseCatalogEntry(course, None)
			result.add(getattr(entry, 'ntiid', None))
			break

	# include NTIIDs of sections
	for instance in get_course_subinstances(course):
		entry = ICourseCatalogEntry(instance, None)
		result.add(getattr(entry, 'ntiid', None))

	result.discard(None)
	result.discard(context.ntiid)
	return _Containers(tuple(result))

# Containers

class _SlideDeck(object):

	__slots__ = (b'videos',)

	def __init__(self, videos):
		self.videos = videos

@component.adapter(INTISlideDeck)
@interface.implementer(ISlideDeckAdapter)
def _slideck_data(context):
	videos = {v.video_ntiid for v in context.Videos or ()}
	return _SlideDeck(videos)

# Bundles

@interface.implementer(IPrincipal)
@component.adapter(IContentPackageBundle)
def bundle_to_principal(library):
	return system_user

def _content_unit_to_bundles(unit):
	result = []
	package = find_interface(unit, IContentPackage, strict=False)
	bundle_catalog = component.queryUtility(IContentPackageBundleLibrary)
	bundles = bundle_catalog.getBundles() if bundle_catalog is not None else ()
	for bundle in bundles or ():
		if package in bundle.ContentPackages:
			result.append(bundle)
	return result

@component.adapter(IContentUnit)
@interface.implementer(IContentPackageBundle)
def _content_unit_to_bundle(unit):
	bundles = _content_unit_to_bundles(unit)
	return bundles[0] if bundles else None

# Context providers

def _get_bundles_from_container(obj):
	results = set()
	catalog = get_library_catalog()
	if catalog:
		containers = catalog.get_containers(obj)
		for container in containers:
			container = find_object_with_ntiid(container)
			bundle = IContentPackageBundle(container, None)
			if bundle is not None:
				results.add(bundle)
	return results

@component.adapter(interface.Interface, IUser)
@interface.implementer(IHierarchicalContextProvider)
def _hierarchy_from_obj(obj, user):
	container_bundles = _get_bundles_from_container(obj)
	results = [(bundle,) for bundle in container_bundles]
	return results

@component.adapter(IContentUnit, IUser)
@interface.implementer(ITopLevelContainerContextProvider)
def _bundles_from_unit(obj, user):
	# We could tweak the adapter above to return
	# all possible bundles, or use the container index.
	bundle = IContentPackageBundle(obj, None)
	result = None
	if bundle:
		result = (bundle,)
	else:
		# Content package
		# TODO same in hierarchy
		package = IContentPackage(obj, None)
		result = (package,)
	return result

@component.adapter(IPost)
@interface.implementer(ITopLevelContainerContextProvider)
def _bundles_from_post(obj):
	bundle = find_interface(obj, IContentPackageBundle, strict=False)
	if bundle is not None:
		return (bundle,)

@component.adapter(ITopic)
@interface.implementer(ITopLevelContainerContextProvider)
def _bundles_from_topic(obj):
	bundle = find_interface(obj, IContentPackageBundle, strict=False)
	if bundle is not None:
		return (bundle,)

@component.adapter(IForum)
@interface.implementer(ITopLevelContainerContextProvider)
def _bundles_from_forum(obj):
	bundle = find_interface(obj, IContentPackageBundle, strict=False)
	if bundle is not None:
		return (bundle,)

def _get_top_level_contexts(obj):
	results = set()
	try:
		top_level_contexts = get_top_level_contexts(obj)
		for top_level_context in top_level_contexts:
			if IContentPackageBundle.providedBy(top_level_context):
				results.add(top_level_context)
	except ForbiddenContextException:
		pass
	return results

@component.adapter(interface.Interface)
@interface.implementer(IJoinableContextProvider)
def _bundles_from_container_object(obj):
	"""
	Using the container index, look for catalog entries that contain
	the given object.
	"""
	results = set()
	bundles = _get_top_level_contexts(obj)
	for bundle in bundles or ():
		# We only want to add publicly available entries.
		if is_readable(bundle):
			results.add(bundle)
	return results

# Containers

@interface.implementer(IPresentationAssetContainer, IContained)
class _PresentationAssetContainer(PersistentMapping,
							   	  PersistentCreatedAndModifiedTimeObject):
	__name__ = None
	__parent__ = None

	_SET_CREATED_MODTIME_ON_INIT = False

	def append(self, item):
		self[item.ntiid] = item

	def extend(self, items):
		for item in items or ():
			self.append(item)

	def assets(self):
		return list(self.values())

	def __setitem__(self, key, value):
		PersistentMapping.__setitem__(self, key, value)

	def __delitem__(self, key):
		PersistentMapping.__delitem__(self, key)

@interface.implementer(IPresentationAssetContainer, IContained)
class _PresentationAssetOOBTree(OOBTree, CreatedAndModifiedTimeMixin):
	__name__ = None
	__parent__ = None

	_SET_CREATED_MODTIME_ON_INIT = False

	def __init__(self, *args, **kwargs):
		OOBTree.__init__(self)
		CreatedAndModifiedTimeMixin.__init__(self, *args, **kwargs)
		
	def append(self, item):
		self[item.ntiid] = item

	def extend(self, items):
		for item in items or ():
			self.append(item)

	def assets(self):
		return list(self.values())

@interface.implementer(IPresentationAssetContainer)
def presentation_asset_items_factory(context):
	try:
		result = context._presentation_asset_item_container
		return result
	except AttributeError:
		result = context._presentation_asset_item_container = _PresentationAssetContainer()
		result.createdTime = time.time()
		result.__parent__ = context
		result.__name__ = '_presentation_asset_item_container'
		return result
