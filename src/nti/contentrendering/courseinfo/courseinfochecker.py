#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from nti.contentrendering.courseinfo import model
from nti.contentrendering.courseinfo import interfaces
from nti.contentrendering.courseinfo import course_info_validation
from zope.schema import getFields

from collections import OrderedDict

class CourseInfoValidation():
	def check_course_instructors(self, course_info, course_info_dict):
		#check instructors listed in the course_info.json
		return course_info.check_instructors(course_info_dict)


	def check_course_prerequisites(self, course_info, course_info_dict):
		#check prerequisites listed in the course_info.json
		return course_info.check_prerequisites(course_info_dict)

	def check_course_credit(self, course_info, course_info_dict):
		#check credit listed in course_info.json
		return course_info.check_credit(course_info_dict)

	def check_course_enrollment(self, course_info, credit_fields):
		#check enrollment information listed course_info.json
		return course_info.check_enrollment_obj(credit_fields)


	def check_course_info(self, course_info_file):
		course_info = course_info_validation.CourseInfoJSONChecker(course_info_file)
		course_info.build_sample_course_info_schema()
		check_json_syntax, course_info_dict= course_info.get_dict_from_file(course_info.file_name)
		check_json_syntax, course_info_dict= course_info.get_dict_from_file(course_info.file_name)
		error_check = False
		error_msg = 'CORRECT'
		unmatched_fields = []
		if course_info_dict!= None:			
			#check course_info.json based on its schema
			checker_list = course_info.check_json_schema(course_info_dict, course_info.course_info_schema)
			error_check, error_msg, unmatched_fields = course_info.checking_result(checker_list)

			if error_check == False or error_msg[0:7] == 'warning':
				#check value of particular fields in course_info_dict
				#make sure that ntiid fields in course_info.json ends with 'course_info'
				check = course_info.check_ntiid_value (course_info_dict, 'course_info')

				if check == True :
					logger.info('ntiid value ends with string >> course_info')
				elif check == False:
					logger.info('invalid ntiid value')
					error_check = True
					error_msg = 'invalid ntiid value'
					unmatched_fields = []
					return error_check, error_msg, unmatched_fields
				else:
					logger.info('there is no ntiid field in the dictionary')


				#check course duration field
				duration_number, duration_kind, duration_days = course_info.check_duration(course_info_dict)
				logger.info("Course duration is %s",duration_kind," is %s",duration_number)
				logger.info("Course duration in days is %s", duration_days)

				#check course instructors field
				logger.info("-------------------------------------------------------")
				logger.info("Check Instructors")
				error_check, error_msg, unmatched_fields = self.check_course_instructors(course_info, course_info_dict)
				if error_check == True and error_msg[0:7] != 'warning':
					return error_check, error_msg, unmatched_fields

				#check course prerequisites field
				logger.info("-------------------------------------------------------")
				logger.info("Check Prerequisites")
				error_check, error_msg, unmatched_fields = self.check_course_prerequisites(course_info, course_info_dict)
				if error_check == True and error_msg[0:7] != 'warning':
					return error_check, error_msg, unmatched_fields

				#check course credit field
				logger.info("-------------------------------------------------------")
				logger.info("Check Credit")
				error_check, error_msg, unmatched_fields = self.check_course_credit(course_info, course_info_dict)
				if error_check == True and error_msg[0:7] != 'warning':
					return error_check, error_msg, unmatched_fields

				#check course enrollment field
				logger.info("-------------------------------------------------------")
				logger.info("Check Enrollment Information")
				if 'credit' in course_info_dict.keys():
					credit_fields = course_info_dict['credit']
					error_check, error_msg, unmatched_fields = self.check_course_enrollment(course_info, credit_fields)
					if error_check == True and error_msg[0:7] != 'warning':
						return error_check, error_msg, unmatched_fields

			else:
				logger.info('course_info.json is not valid')
				return error_check, error_msg, unmatched_fields
		else:
			logger.info("JSON Format Error")
			error_check = True
			error_msg = 'JSON format error: course_info.json syntax is incorrect'
			unmatched_fields = []
			return error_check, error_msg, unmatched_fields

		return error_check, error_msg, unmatched_fields


#logger.info("start checking")
#course_info_file = '/Users/ega/Projects/AoPSBooks5/CHEM4970_Chemistry_of_Beer/Templates/Themes/Generic/course_info.json'
#check = CourseInfoValidation()
#check.check_course_info(course_info_file)

