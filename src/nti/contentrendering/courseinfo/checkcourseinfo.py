#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

from zope import interface

from .. import interfaces
interface.moduleProvides(interfaces.IRenderedBookValidator)

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
		