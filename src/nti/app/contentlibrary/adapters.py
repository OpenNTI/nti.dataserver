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

from zope.interface.common.mapping import IMapping

from zope.intid.interfaces import IIntIds

from zope.location.interfaces import IContained

from zope.security.interfaces import IPrincipal

from persistent.mapping import PersistentMapping

from pyramid.location import lineage

from nti.appserver.context_providers import get_top_level_contexts

from nti.appserver.interfaces import IJoinableContextProvider
from nti.appserver.interfaces import ForbiddenContextException
from nti.appserver.interfaces import IHierarchicalContextProvider
from nti.appserver.interfaces import ITopLevelContainerContextProvider

from nti.appserver.pyramid_authorization import is_readable

from nti.assessment.interfaces import IQAssessment
from nti.assessment.interfaces import IQSubmittable

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary

from nti.contentlibrary.indexed_data import get_library_catalog

from nti.contentlibrary.indexed_data.interfaces import INTIIDAdapter
from nti.contentlibrary.indexed_data.interfaces import INamespaceAdapter
from nti.contentlibrary.indexed_data.interfaces import IContainersAdapter
from nti.contentlibrary.indexed_data.interfaces import IContainedTypeAdapter

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseOutlineNode
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.contenttypes.presentation import iface_of_asset

from nti.contenttypes.presentation.interfaces import IPresentationAsset,\
	INTISlide, INTISlideVideo
from nti.contenttypes.presentation.interfaces import ICoursePresentationAsset
from nti.contenttypes.presentation.interfaces import IPackagePresentationAsset
from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.contenttypes.courses.index import IX_PACKAGES
from nti.contenttypes.courses.index import IX_SITE as IX_COURSES_SITE

from nti.contenttypes.courses.utils import get_courses_catalog
from nti.contenttypes.courses.utils import get_course_subinstances

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IForum

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import system_user

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.schema.interfaces import find_most_derived_interface

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

@component.adapter(IQAssessment)
@interface.implementer(IContainedTypeAdapter)
def _assessment_to_contained_type(context):
	provided = find_most_derived_interface(context, IQAssessment)
	return _Type(provided.__name__)

@component.adapter(IQSubmittable)
@interface.implementer(IContainedTypeAdapter)
def _submittable_to_contained_type(context):
	provided = find_most_derived_interface(context, IQSubmittable)
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

@component.adapter(IQAssessment)
@interface.implementer(INamespaceAdapter)
def _assessment_to_namespace(context):
	return _package_lineage_to_namespace(context)

@component.adapter(IQSubmittable)
@interface.implementer(INamespaceAdapter)
def _submittable_to_namespace(context):
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

@component.adapter(IQAssessment)
@interface.implementer(INTIIDAdapter)
def _assessment_to_ntiid(context):
	return _NTIID(context.ntiid)

@component.adapter(IQSubmittable)
@interface.implementer(INTIIDAdapter)
def _submittable_to_ntiid(context):
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
	if package is not None and folder != None:
		catalog = get_courses_catalog()
		containers = set(result.containers)
		intids = component.getUtility(IIntIds)
		query = {
			IX_PACKAGES: {'any_of':(package.ntiid,) },
			IX_COURSES_SITE: {'any_of':(folder.__name__,)}
		}
		for uid in catalog.apply(query) or ():
			course = intids.queryObject(uid)
			entry = ICourseCatalogEntry(course, None)
			if entry != None:
				containers.add(entry.ntiid)
		result = _Containers(tuple(containers))
	return result

@component.adapter(INTISlide)
@interface.implementer(IContainersAdapter)
def _slide_asset_to_containers(context):
	result = _pacakge_asset_to_containers(context)
	if context.__parent__ is not None and context.__parent__.ntiid:
		containers = set(result.containers)
		containers.add(context.__parent__.ntiid)
		result = _Containers(tuple(containers))
	return result

@component.adapter(INTISlideVideo)
@interface.implementer(IContainersAdapter)
def _slidevideo_asset_to_containers(context):
	result = _slide_asset_to_containers(context)
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

@component.adapter(IQAssessment)
@interface.implementer(IContainersAdapter)
def _assessment_to_containers(context):
	result = _package_lineage_to_containers(context)
	return result

@component.adapter(IQSubmittable)
@interface.implementer(IContainersAdapter)
def _submittable_to_containers(context):
	result = _package_lineage_to_containers(context)
	return result

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

@interface.implementer(IPresentationAssetContainer, IContained, IMapping)
class _PresentationAssetContainer(PersistentMapping,
							   	  PersistentCreatedAndModifiedTimeObject):
	__name__ = None
	__parent__ = None
	_SET_CREATED_MODTIME_ON_INIT = False

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
