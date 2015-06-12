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

from nti.assessment.interfaces import IQPoll
from nti.assessment.interfaces import IQSurvey
from nti.assessment.interfaces import IQuestion
from nti.assessment.interfaces import IQuestionSet
from nti.assessment.interfaces import IQAssignment

from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.indexed_data.interfaces import IContainedTypeAdapter

from nti.contenttypes.presentation.interfaces import INTIAudio
from nti.contenttypes.presentation.interfaces import INTIVideo
from nti.contenttypes.presentation.interfaces import INTISlide
from nti.contenttypes.presentation.interfaces import INTITimeline
from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import INTISlideVideo
from nti.contenttypes.presentation.interfaces import INTIRelatedWorkRef

from nti.dataserver.interfaces import system_user

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
	return _Type('INTIAudio')

@component.adapter(INTIVideo)
@interface.implementer(IContainedTypeAdapter)
def _video_to_contained_type(context):
	return _Type('INTIVideo')

@component.adapter(INTISlide)
@interface.implementer(IContainedTypeAdapter)
def _slide_to_contained_type(context):
	return _Type('INTISlide')

@component.adapter(INTITimeline)
@interface.implementer(IContainedTypeAdapter)
def _timeline_to_contained_type(context):
	return _Type('INTITimeline')

@component.adapter(INTISlideDeck)
@interface.implementer(IContainedTypeAdapter)
def _slidedeck_to_contained_type(context):
	return _Type('INTISlideDeck')

@component.adapter(INTISlideVideo)
@interface.implementer(IContainedTypeAdapter)
def _slidevideo_to_contained_type(context):
	return _Type('INTISlideVideo')

@component.adapter(INTIRelatedWorkRef)
@interface.implementer(IContainedTypeAdapter)
def _related_to_contained_type(context):
	return _Type('INTIRelatedWorkRef')

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
