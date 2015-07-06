#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.security.interfaces import IPrincipal

from nti.appserver.interfaces import IJoinableContextProvider
from nti.appserver.interfaces import IHierarchicalContextProvider
from nti.appserver.interfaces import ITopLevelContainerContextProvider

from nti.appserver.pyramid_authorization import is_readable

from nti.assessment.interfaces import IQPoll
from nti.assessment.interfaces import IQSurvey
from nti.assessment.interfaces import IQuestion
from nti.assessment.interfaces import IQuestionSet
from nti.assessment.interfaces import IQAssignment
from nti.assessment.interfaces import IQAssessment

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary

from nti.contentlibrary.indexed_data import get_catalog
from nti.contentlibrary.indexed_data import NTI_AUDIO_TYPE
from nti.contentlibrary.indexed_data import NTI_VIDEO_TYPE
from nti.contentlibrary.indexed_data import NTI_SLIDE_TYPE
from nti.contentlibrary.indexed_data import NTI_TIMELINE_TYPE
from nti.contentlibrary.indexed_data import NTI_SLIDE_DECK_TYPE
from nti.contentlibrary.indexed_data import NTI_SLIDE_VIDEO_TYPE
from nti.contentlibrary.indexed_data import NTI_RELATED_WORK_TYPE
from nti.contentlibrary.indexed_data.interfaces import IContainedTypeAdapter

from nti.contenttypes.presentation.interfaces import INTIAudio
from nti.contenttypes.presentation.interfaces import INTIVideo
from nti.contenttypes.presentation.interfaces import INTISlide
from nti.contenttypes.presentation.interfaces import INTITimeline
from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import INTISlideVideo
from nti.contenttypes.presentation.interfaces import INTIDiscussionRef
from nti.contenttypes.presentation.interfaces import INTIRelatedWorkRef
from nti.contenttypes.presentation.interfaces import IPresentationAsset
from nti.contenttypes.presentation.interfaces import INTILessonOverview
from nti.contenttypes.presentation.interfaces import INTICourseOverviewGroup
from nti.contenttypes.presentation.interfaces import INTICourseOverviewSpacer

from nti.dataserver.interfaces import system_user

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.schema.interfaces import find_most_derived_interface

from nti.traversal.traversal import find_interface

@interface.implementer(IPrincipal)
@component.adapter(IContentPackageBundle)
def bundle_to_principal(library):
	return system_user

class _Type(object):

	__slots__ = (b'type',)

	def __init__(self, type_):
		self.type = type_

@component.adapter(INTIAudio)
@interface.implementer(IContainedTypeAdapter)
def _audio_to_contained_type(context):
	return _Type(NTI_AUDIO_TYPE)

@component.adapter(INTIVideo)
@interface.implementer(IContainedTypeAdapter)
def _video_to_contained_type(context):
	return _Type(NTI_VIDEO_TYPE)

@component.adapter(INTISlide)
@interface.implementer(IContainedTypeAdapter)
def _slide_to_contained_type(context):
	return _Type(NTI_SLIDE_TYPE)

@component.adapter(INTITimeline)
@interface.implementer(IContainedTypeAdapter)
def _timeline_to_contained_type(context):
	return _Type(NTI_TIMELINE_TYPE)

@component.adapter(INTISlideDeck)
@interface.implementer(IContainedTypeAdapter)
def _slidedeck_to_contained_type(context):
	return _Type(NTI_SLIDE_DECK_TYPE)

@component.adapter(INTISlideVideo)
@interface.implementer(IContainedTypeAdapter)
def _slidevideo_to_contained_type(context):
	return _Type(NTI_SLIDE_VIDEO_TYPE)

@component.adapter(INTIRelatedWorkRef)
@interface.implementer(IContainedTypeAdapter)
def _related_to_contained_type(context):
	return _Type(NTI_RELATED_WORK_TYPE)

@component.adapter(INTIDiscussionRef)
@interface.implementer(IContainedTypeAdapter)
def _discussionref_to_contained_type(context):
	return _Type('INTIDiscussionRef')

@component.adapter(INTILessonOverview)
@interface.implementer(IContainedTypeAdapter)
def _lessonoverview_to_contained_type(context):
	return _Type('INTILessonOverview')

@component.adapter(INTICourseOverviewGroup)
@interface.implementer(IContainedTypeAdapter)
def _courseoverview_to_contained_type(context):
	return _Type('INTICourseOverviewGroup')

@component.adapter(INTICourseOverviewSpacer)
@interface.implementer(IContainedTypeAdapter)
def _courseoverviewspacer_to_contained_type(context):
	return _Type('INTICourseOverviewSpacer')

@component.adapter(IPresentationAsset)
@interface.implementer(IContainedTypeAdapter)
def _asset_to_contained_type(context):
	provided = find_most_derived_interface(context, IPresentationAsset)
	return _Type(provided.__name__)

@component.adapter(IQAssignment)
@interface.implementer(IContainedTypeAdapter)
def _assignment_to_contained_type(context):
	return _Type('IQAssignment')

@component.adapter(IQuestionSet)
@interface.implementer(IContainedTypeAdapter)
def _questionset_to_contained_type(context):
	return _Type('IQuestionSet')

@component.adapter(IQuestion)
@interface.implementer(IContainedTypeAdapter)
def _question_to_contained_type(context):
	return _Type('IQuestion')

@component.adapter(IQSurvey)
@interface.implementer(IContainedTypeAdapter)
def _survey_to_contained_type(context):
	return _Type('IQSurvey')

@component.adapter(IQPoll)
@interface.implementer(IContainedTypeAdapter)
def _poll_to_contained_type(context):
	return _Type('IQPoll')

@component.adapter(IQAssessment)
@interface.implementer(IContainedTypeAdapter)
def _assessment_to_contained_type(context):
	provided = find_most_derived_interface(context, IQAssessment)
	return _Type(provided.__name__)

def _content_unit_to_bundles(unit):
	result = []
	package = find_interface(unit, IContentPackage, strict=False)
	bundle_catalog = component.queryUtility(IContentPackageBundleLibrary)

	for bundle in bundle_catalog.getBundles() or ():
		if package in bundle.ContentPackages:
			result.append( bundle )
	return result

@interface.implementer(IContentPackageBundle)
@component.adapter(IContentUnit)
def _content_unit_to_bundle(unit):
	bundles = _content_unit_to_bundles(unit)
	return bundles[0] if bundles else None

def _get_bundles_from_container( obj ):
	catalog = get_catalog()
	results = set()
	if catalog:
		containers = catalog.get_containers(obj)
		for container in containers:
			container = find_object_with_ntiid(container)
			bundle = IContentPackageBundle(container, None)
			if bundle is not None:
				results.add(bundle)
	return results

@interface.implementer(IHierarchicalContextProvider)
@component.adapter(interface.Interface)
def _hierarchy_from_obj(obj):
	container_bundles = _get_bundles_from_container( obj )
	results = [(bundle,) for bundle in container_bundles]
	return results

@interface.implementer(ITopLevelContainerContextProvider)
@component.adapter( IContentUnit )
def _bundles_from_unit(obj):
	# We could tweak the adapter above to return
	# all possible bundles, or use the container index.
	# TODO Do we want to return top-level ContentPackages here?
	# How would we know if the CP is not contained by
	# another object?
	bundle = IContentPackageBundle(obj, None)
	if bundle:
		return (bundle,)

def _get_top_level_contexts( obj ):
	results = set()
	for top_level_contexts in component.subscribers( (obj,),
													ITopLevelContainerContextProvider ):
		top_level_contexts = []
		for top_level_context in top_level_contexts:
			if IContentPackageBundle.providedBy( top_level_context ):
				results.add( top_level_context )
	return results

@interface.implementer(IJoinableContextProvider)
@component.adapter(interface.Interface)
def _bundles_from_container_object(obj):
	"""
	Using the container index, look for catalog entries that contain
	the given object.
	"""
	results = set()
	bundles = _get_top_level_contexts( obj )
	for bundle in bundles or ():
		# We only want to add publicly available entries.
		if is_readable(bundle):
			results.add(bundle)
	return results
