#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
from collections import Mapping

import simplejson as json

from zope import interface
from zope.schema.interfaces import RequiredMissing

from nti.externalization.internalization import find_factory_for
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.internalization import update_from_external_object

from .model import Credit
from .model import Schedule
from .model import CourseInfo
from .model import Enrollment
from .model import Instructor
from .model import Prerequisite

MIMETYPE = StandardExternalFields.MIMETYPE

def validate(data):
	assert isinstance(data, Mapping)
	
	# complete mime types
	if MIMETYPE not in data:
		data[MIMETYPE] = CourseInfo.mimeType
	
	for inst in data.get('instructors',()):
		if isinstance(inst, Mapping) and MIMETYPE not in inst:
			inst[MIMETYPE] = Instructor.mimeType
			
	for preq in data.get('prerequisites',()):
		if isinstance(preq, Mapping) and MIMETYPE not in preq:
			preq[MIMETYPE] = Prerequisite.mimeType
	
	for credit in data.get('credit', ()):
		if MIMETYPE not in credit:
			credit[MIMETYPE] = Credit.mimeType
		enrollment = credit.get('enrollment')
		if isinstance(enrollment, Mapping) and MIMETYPE not in enrollment:
			credit['enrollment'][MIMETYPE] = Enrollment.mimeType
			
	schedule = data.get('schedule')
	if isinstance(schedule, Mapping) and MIMETYPE not in schedule:
		schedule[MIMETYPE] = Schedule.mimeType

	# start validation
	factory = find_factory_for(data)
	course_info = factory()
	try:
		update_from_external_object(course_info, data, notify=False)
	except RequiredMissing:
		exc_info = sys.exc_info()
		raise Exception("Missing data. Field %s",exc_info[1].args[0],)
	except Exception:
		raise
	
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
	
# 	# derive preview information if not provided.
# 	if 'isPreview' in info_json_dict:
# 		catalog_entry.Preview = info_json_dict['isPreview']
# 	else:
# 		_quiet_delattr(catalog_entry, 'Preview')
# 		if catalog_entry.StartDate and datetime.datetime.utcnow() < catalog_entry.StartDate:
# 			assert catalog_entry.Preview
			
	return result

UTF8_ALIASES = ('utf-8', 'utf8', 'utf_8', 'utf', 'u8')

LATIN1_ALIASES = ('latin-1', 'latin1',  'latin', 'l1', 'cp819', '8859',
				  'iso8859-1', 'iso-8859-1')

def _try_unicode(obj, encoding='utf-8', errors='replace'):
	if isinstance(obj, basestring):
		encoding = (encoding or '').lower()
		if isinstance(obj, unicode):
			return obj
		if encoding in UTF8_ALIASES:
			return unicode(obj, 'utf-8', errors)
		if encoding in LATIN1_ALIASES:
			return unicode(obj, 'latin-1', errors)
		return obj.decode(encoding, errors)
	return obj

def convert(data, encoding='utf-8'):
	if isinstance(data, Mapping):
		return {convert(key): convert(value) for key, value in data.iteritems()}
	elif isinstance(data, (list, tuple)):
		return [convert(element) for element in data]
	else:
		return _try_unicode(data, encoding)

def validate_file(source):
	if hasattr(source, 'read'):
		data = json.load(source)
	else:
		with open(source, "r") as fp:
			data = json.load(fp)

	data = convert(data) # make sure we have unicode
	return validate(data)

def check(book):
	contentPath = os.path.dirname(book.toc.root_topic.filename )
	course_info_file = os.path.join(contentPath, 'course_info.json')
	if not os.path.exists(course_info_file):
		logger.warn("Course info file was not found")
		return
	
	for msg in validate_file(course_info_file):
		logger.warn(msg)

from .. import interfaces
interface.moduleProvides(interfaces.IRenderedBookValidator)
