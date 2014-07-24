#!/usr/bin/env python
# -*- coding: utf-8 -*

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson as json
from . import model


import zope.schema
from collections import OrderedDict

import datetime
from .schema import DateTime 

class CourseInfoValidation(object):

	def __init__(self, file_name):
		self.file_name = file_name

	def build_sample_course_info_schema(self):
		self.prerequisite_o = model.Prerequisite(id = "CHEM 3000-001", title="Senior standing or instructor permission")
		self.enrollment_o = model.Enrollment(label = "Enroll with Ozone", url = "http://ozone.ou.edu/")
		self.credit_o = model.Credit(hours = 1, enrollment = self.enrollment_o)
		self.instructor_o1 = model.Instructor(defaultphoto = "images/Morvant.png", username = "morv1533",
			name = "Mark Morvant, PhD", title = "Professor, Department of Chemistry")
		self.instructor_o2 = model.Instructor(defaultphoto = "images/Sims.png", username = "sims2543",
			name = "Paul Sims, PhD", title = "Associate Professor, Department of Chemistry")
		self.course_info_schema = model.CourseInfo(ntiid = "tag:nextthought.com,2011-10:OU-HTML-CHEM4970_Chemistry_of_Beer.course_info",
			id = "CHEM 4970-001", school = "Department of Chemistry and Biochemistry at the University of Oklahoma",
			is_non_public = False, term = "Fall 2014", startDate = "2014-01-13T06:00:00+00:00", duration = "16 Weeks",
			isPreview = True, instructors = [self.instructor_o1, self.instructor_o2],
			video =  "kaltura://1500101/0_bxfatwxs/",
			title = "Chemistry of Beer",
			description = "This course covers the process of brewing from grain to final bottle product and the chemical and biochemical process involved in each step. Students will be required to utilize previous knowledge in General and Organic chemistry to understand: analytical techniques in brewing, chemistry of the ingredients and products, and the molecules involved in the biochemical processes.  During the course, students will also learn the similarities and differences between beer styles, home and commercial brewing processes, and analytical techniques.  There is a great deal of Biochemistry and Organic Chemistry involved in the malting, mashing and fermentation process and understanding the chemistry behind the flavor, aroma, and color of beer. Students should have a basic knowledge of general and organic chemistry.",
			credit = [self.credit_o],
			prerequisites = [self.prerequisite_o]
			)

	def find_matched_fields(self, list1, list2):
		"""
		find matching values  between two lists
		(for example between course_info schema fields and course_info dictionary keys)
		"""
		return list(set(list1) & set(list2))

	def find_unmatched_fields(self, list1, list2):
		"""
		find non matching values between two lists
		"""
		return list(set(list1) - set(list2))

	def get_schema_fields(self, data_schema):
		"""
		get all fields in course_info schema
		"""
		ifaces = data_schema.__provides__.__iro__

		logger.info("Show course info instance variable names and their values")
		# get field names from all course_info interfaces
		data_schema_fields_type = OrderedDict()
		data_schema_fields_name = []
		data_schema_fields_required = OrderedDict()
		for iface in ifaces:
			fields = zope.schema.getFieldsInOrder(iface)
			for name, field in fields:
				data_schema_fields_type[name] = getattr(data_schema, name, None)
				data_schema_fields_required[name] = field.required
				data_schema_fields_name.append(name)

		return data_schema_fields_name, data_schema_fields_type, data_schema_fields_required


	def get_dict_from_file(self, file_name):
		"""
		Read course_info.json file
		Transform its content into python object and check if the json sytax is valid
		Return course_info.json in the form of python object (course_info_dict)
		"""
		check = 0
		dict_from_string = {}
		warning_msg = ''
		try:
			f = open(file_name, 'r')
			file_content = f.read()
			try:
				dict_from_string = json.loads(file_content)
				check = 1
			except (json.JSONDecodeError, ValueError, KeyError, TypeError):
				check = 0
				logger.info('JSON format error')
				warning_msg = 'JSON format error'
				return check, dict_from_string, warning_msg
		except IOError:
			logger.info('Can not find file or read data course_info.json')
			check = 2
			warning_msg = 'Can not find file or read data course_info.json'
			return check, dict_from_string, warning_msg
		else:
			f.close()
			return check, dict_from_string, warning_msg

	def check_missing_fields(self, json_dict, data_schema_fields):
		"""
		check whether json_dict (obtained from course_info.json) has missing fields
		"""
		check = False
		warning_msg = ''
		missing_fields = self.find_unmatched_fields(data_schema_fields, json_dict.keys())
		if len(missing_fields) > 0:
			check = False
			warning_msg = 'json file has some missing fields compare to its schema'
			logger.info("%s %s", warning_msg, missing_fields)
		else:
			check = True
		return check, warning_msg, missing_fields

	def check_additional_fields(self, json_dict, data_schema_fields):
		"""
		Check whether the course_info dict obtained from course_info.json
		has all the required fields in the course info schema.
		"""
		check = False
		warning_msg = ''
		additional_field_in_dict = self.find_unmatched_fields(json_dict.keys(), data_schema_fields)

		if len(json_dict.keys()) > len(data_schema_fields):
			check = False
			warning_msg = 'json file contains more fields than defined fields defined in its schema'
		else:
			matched_fields = self.find_matched_fields(json_dict.keys(), data_schema_fields)
			unmatched_fields = self.find_unmatched_fields(json_dict.keys(), matched_fields)
			if len(unmatched_fields) == 0:
				#course_info.json has all fields defined in course_info schema
				check = True
			elif len(unmatched_fields) > 0:
				check = False
				warning_msg = 'json file contains fields not defined in its schema'
				logger.info("%s %s", warning_msg, unmatched_fields)

		return check, matched_fields, unmatched_fields, additional_field_in_dict, warning_msg


	def check_field_type(self, json_dict, data_schema_field_types):
		"""
		check if fields has the same type
		"""
		check = True
		matched_fields_type = []
		unmatched_fields_type = []
		for key in json_dict.keys() :
			if key in data_schema_field_types :
				#logger.info (key , "type in dict is", type(json_dict[key]),
				#" - ", key, "type in schema is ", type(data_schema_field_types[key]))
				if type(json_dict[key]) != type(data_schema_field_types[key]):
					if (type(json_dict[key]) is str and type(data_schema_field_types[key]) is unicode) or (type(json_dict[key]) is dict and key == 'enrollment'):
						matched_fields_type.append(key)
					elif(type(data_schema_field_types[key]) is datetime.datetime):
						if (DateTime().fromUnicode(json_dict[key])):
							matched_fields_type.append(key)
						else:
							unmatched_fields_type.append(key)
					else:
						logger.info("%s has unmatched field type", key)
						unmatched_fields_type.append(key)
						check = False

		return check, matched_fields_type, unmatched_fields_type


	def check_required_fields(self, json_dict, data_schema_fields_required):
		"""
		check if json_dict (json_dict) have all required fields
		"""
		check = True
		missing_required_fields = []
		for key in data_schema_fields_required.keys():
			if data_schema_fields_required[key] == True and key not in json_dict.keys():
				missing_required_fields.append(key)
				check = False
				logger.info ("json file does not contain the required fields %s", key)
		return check, missing_required_fields


	def check_ntiid_value (self, course_info_dict, required_string):
		"""
		check nttiid value
		"""
		if 'ntiid' in course_info_dict.keys():
			ntiid_value = course_info_dict['ntiid']
			str_end_len = len(required_string)
			ntiid_len = len(ntiid_value)

			if ntiid_value[(ntiid_len - str_end_len) : ntiid_len] == required_string:
				return True
			else:
				return False
		else:
			return None


	def check_duration(self, course_info_dict):
		"""
		check duration value
		"""
		if 'duration' in course_info_dict.keys():
			duration_number, duration_kind = course_info_dict['duration'].split()
			duration_days = datetime.timedelta(**{duration_kind.lower():int(duration_number)})
			return duration_number, duration_kind, duration_days
		else:
			return None



	def check_json_schema(self, json_dict, data_schema):
		"""
		compare dictionary from json file with its schema
		"""

		json_validation_report = []
		data_schema_fields_name, data_schema_fields_type, data_schema_fields_required = self.get_schema_fields(data_schema)


		#check required field
		check_missing_required_fields, missing_required_fields = self.check_required_fields(json_dict, data_schema_fields_required);
		if len(missing_required_fields) == 0:
			logger.info("All required fields are available")
		else:
			logger.info("json file is missing the following required fields:")
			logger.info("%s",missing_required_fields)
		json_validation_report.append(check_missing_required_fields)
		json_validation_report.append(missing_required_fields)

		#check whether the json file has missing fields compare to fields defined in the schema
		check_dict, warning_msg1, missing_fields = self.check_missing_fields(json_dict, data_schema_fields_name)
		if check_dict == False:
			logger.info("%s %s", warning_msg1, missing_fields)
			logger.info("%s", missing_fields)
		else:
			logger.info("json file has all the schema fields")
		json_validation_report.append(check_dict)
		json_validation_report.append(warning_msg1)
		json_validation_report.append(missing_fields)

		#check whether course_info.json has additional fields not defined in the schema
		check_field_name, matched_fields, unmatched_fields, additional_field_in_dict, warning_msg2 = self.check_additional_fields(json_dict, data_schema_fields_name)
		if check_field_name == True:
			logger.info("all fields in the json file has the same name with its schema")
		else:
			logger.info("%s", warning_msg2)
			logger.info("%s", unmatched_fields)
		json_validation_report.append(check_field_name)
		json_validation_report.append(matched_fields)
		json_validation_report.append(unmatched_fields)
		json_validation_report.append(additional_field_in_dict)
		json_validation_report.append(warning_msg2)

		#check fields type
		check_type, matched_fields_type, unmatched_fields_type = self.check_field_type(json_dict, data_schema_fields_type)
		if check_type == True:
			logger.info("All field types in json file match with fields type in the schema")
		else:
			logger.info("The following fields have different types than the schema")
			logger.info("%s", unmatched_fields_type)
		json_validation_report.append(check_type)
		json_validation_report.append(matched_fields_type)
		json_validation_report.append(unmatched_fields_type)

		return json_validation_report


	def check_instructors(self, course_info_dict):
		"""
		check instructor fields
		"""
		error_check = False
		error_msg = ''
		unmatched_fields = []
		if 'instructors' in course_info_dict.keys():
			instructor_list = course_info_dict['instructors']
			for instructor_dict in instructor_list:
				checker_list = self.check_json_schema(instructor_dict, self.instructor_o1)
				#print (len (checker_list))
				error_check, error_msg, unmatched_fields = self.checking_result(checker_list)
		return error_check, error_msg, unmatched_fields

	def check_prerequisites(self, course_info_dict):
		"""
		check prerequisite fields
		"""
		error_check = False
		error_msg = ''
		unmatched_fields = []
		if 'prerequisites' in course_info_dict.keys():
			prerequisite_list = course_info_dict['prerequisites']
			for prerequisite_dict in prerequisite_list:
				checker_list = self.check_json_schema(prerequisite_dict, self.prerequisite_o)
				error_check, error_msg, unmatched_fields = self.checking_result(checker_list)
		return error_check, error_msg, unmatched_fields

	def check_credit (self, course_info_dict):
		"""
		check credit fields
		"""
		error_check = False
		error_msg = ''
		unmatched_fields = []
		if 'credit' in course_info_dict.keys():
			credit_fields = course_info_dict['credit']
			for credit_dict in credit_fields:
				checker_list = self.check_json_schema(credit_dict, self.credit_o)
				error_check, error_msg, unmatched_fields = self.checking_result(checker_list)

		return error_check, error_msg, unmatched_fields


	def check_enrollment_obj(self, credit_fields):
		"""
		check enrollment fields
		"""
		error_check = False
		error_msg = ''
		unmatched_fields = []
		for credit_dict in credit_fields:
			if 'enrollment' in credit_dict.keys():
				enrollment_dict = credit_dict['enrollment']
				checker_list = self.check_json_schema(enrollment_dict, self.enrollment_o)
				error_check, error_msg, unmatched_fields = self.checking_result(checker_list)
		return error_check, error_msg, unmatched_fields


	def checking_result(self, json_validation_report):
		"""
		view checking result
		json_validation_report[0] : check_missing_required_fields
		json_validation_report[1] : missing_required_fields
		json_validation_report[2] : check_dict
		json_validation_report[3] : warning_msg1
		json_validation_report[4] : missing_fields
		json_validation_report[5] : check_field_name
		json_validation_report[6] : matched_fields
		json_validation_report[7] : unmatched_fields
		json_validation_report[8] : additional_field_in_dict
		json_validation_report[9] : warning_msg2
		json_validation_report[10] : check_type
		json_validation_report[11] : matched_fields_type
		json_validation_report[12] : unmatched_fields_type
		"""

		error_check = False
		warning_check = False
		if json_validation_report[0] == False:
			error_check = True
			missing_required_fields = json_validation_report[1]
			error_msg = 'missing required fields in the course_info.json file'
			return error_check, error_msg, missing_required_fields
		elif json_validation_report[2] == False:
			warning_check = True
			warning_msg = 'warning: some fields defined in the courseinfo schema is not in course_info.json'
			missing_fields = json_validation_report[4]
			return warning_check, warning_msg, missing_fields
		elif json_validation_report [5] == False:
			error_check = True
			error_msg = "course_info.json has different fields  than courseinfo schema"
			unmatched_fields = json_validation_report[7]
			return error_check, error_msg, unmatched_fields
		elif json_validation_report[10] == False:
			error_check = True
			error_msg = 'Some fields in the course_info.json contain different value types than its schema'
			unmatched_fields_type = json_validation_report[12]
			return error_check, error_msg, unmatched_fields_type
		else:
			error_check = False
			error_msg = 'course_info.json is valid'
			unmatched_fields = []
			return error_check, error_msg, unmatched_fields_type
