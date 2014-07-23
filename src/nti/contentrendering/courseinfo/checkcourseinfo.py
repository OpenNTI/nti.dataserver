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

from zope import interface

from .. import interfaces
interface.moduleProvides(interfaces.IRenderedBookValidator)

from nti.externalization.internalization import find_factory_for
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.internalization import update_from_external_object

from .model import CourseInfo
from .courseinfochecker import CourseInfoJSONChecker

def check(book):
	contentPath = os.path.dirname(book.toc.root_topic.filename )
	course_info_file = os.path.join(contentPath, 'course_info.json')

	if not os.path.exists( course_info_file ):
		logger.info('There is no course_info.json in this content')
		return
	
	course_info = CourseInfoJSONChecker()
	error_check, error_msg, unmatched_fields = \
		 course_info.check_course_info(course_info_file)

	if error_check == True and error_msg[0:7] != 'warning':
		logger.info(error_msg)
		logger.info(unmatched_fields)
		raise CourseInfoError(error_msg, unmatched_fields)
	elif error_check == True and error_msg[0:7] == 'warning':
		logger.info(error_msg)
		logger.info(unmatched_fields)
	else: 
		logger.info('course_info.json is valid')
	
class CourseInfoError(Exception):
	def __init__(self, error_msg, unmatched_fields):
		self.error_msg = error_msg
		self.unmatched_fields = unmatched_fields
	def __str__(self):
		self.value = self.error_msg + ':'.join(self.unmatched_fields)
		return repr(self.value )	

def check2(book):
	contentPath = os.path.dirname(book.toc.root_topic.filename )
	course_info_file = os.path.join(contentPath, 'course_info.json')
	if not os.path.exists(course_info_file):
		logger.warn("Course info file was not found")
		return
	
	with open(course_info_file, "r") as fp:
		data = simplejson.load(fp, encoding="UTF-8")
		
	# update/add mime type
	data[StandardExternalFields.MIMETYPE] = CourseInfo.mimeType
	
	factory = find_factory_for(data)
	course_info = factory()
	try:
		update_from_external_object(course_info, data, notify=False)
	except Exception,e:
		raise CourseInfoError(str(e))
	
	# log warnings
	if not course_info.schedule:
		logger.warn("No course schedule was specified")
	
	# check instructors
	for instructor in course_info.instructors:
		name = instructor.name
		if not instructor.username:
			logger.warn("username for instructor %s was not specified", name)
		if not instructor.userid:
			logger.warn("userid for instructor %s was not specified", name)
		