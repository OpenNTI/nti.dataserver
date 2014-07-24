#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import simplejson
import collections

from zope import interface

from nti.externalization.internalization import find_factory_for
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.internalization import update_from_external_object

from .model import CourseInfo

class CourseInfoError(Exception):
	pass

def validate(source):
	if hasattr(source, 'read'):
		data = simplejson.load(source)
	else:
		with open(source, "r") as fp:
			data = simplejson.load(fp, encoding="UTF-8")
		
	assert isinstance(data, collections.Mapping)
	
	# add mime type
	if StandardExternalFields.MIMETYPE not in data:
		data[StandardExternalFields.MIMETYPE] = CourseInfo.mimeType
	
	factory = find_factory_for(data)
	course_info = factory()
	try:
		update_from_external_object(course_info, data, notify=False)
	except Exception,e:
		raise CourseInfoError(str(e))
	
	result = []
	
	if course_info.is_non_public is None:
		result.append("Course privacy flag was not specified")
		
	if not course_info.term:
		result.append("Course term was not specified")
	
	if not course_info.startDate:
		result.append("Course start date was not specified")
	
	if not course_info.duration:
		result.append("Course duration was not specified")
	
	if course_info.isPreview is None:
		result.append("Course preview flag was not specified")
	
	# check course schedule
	if not course_info.schedule:
		result.append("No course schedule was specified")
	else:
		if not course_info.schedule.days:
			result.append("Course schedule days not were specified")
		if not course_info.schedule.times:
			result.append("Course schedule time slots were not specified")
	
	# prerequisites
	if not course_info.prerequisites:
		result.append("No course prerequisites were specified")
	else:
		for idx, prereq in enumerate(course_info.prerequisites):
			if not prereq.id:
				result.append("No prerequisite id was specified at index %s" % idx)
			if not prereq.title:
				result.append("No prerequisite title was specified at index %s" % idx)

	# check instructors
	for instructor in course_info.instructors:
		name = instructor.name
		if not instructor.username:
			result.append("username for instructor %s was not specified" % name)
		if not instructor.userid:
			result.append("userid for instructor %s was not specified" % name)
	
	return result

def check(book):
	contentPath = os.path.dirname(book.toc.root_topic.filename )
	course_info_file = os.path.join(contentPath, 'course_info.json')
	if not os.path.exists(course_info_file):
		logger.warn("Course info file was not found")
		return
	
	for msg in validate(course_info_file):
		logger.warn(msg)

from .. import interfaces
interface.moduleProvides(interfaces.IRenderedBookValidator)