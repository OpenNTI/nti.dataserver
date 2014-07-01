#!/usr/bin/env python
# -*- coding: utf-8 -*

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson as json
from nti.contentrendering.courseinfo import model
from nti.contentrendering.courseinfo import interfaces

import zope.schema
from collections import OrderedDict

import datetime


class CourseInfoJSONChecker():

	def __init__(self, data_schema, file_name):
		self.data_schema = data_schema
		self.file_name = file_name

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
		
		print("Show course info instance variable names and their values")
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
				print (name, type(data_schema_fields_type[name]), field.required)
		return data_schema_fields_name, data_schema_fields_type, data_schema_fields_required


	def get_dict_from_file(self, file_name):
		"""
		Read course_info.json file
		Transform its content into python object and check if the json sytax is valid
		Return course_info.json in the form of python object (course_info_dict)
		"""
		
		f = open(file_name, 'r')
		file_content = f.read()
		check = False
		try: 
			dict_from_string = json.loads(file_content)
			check = True
		except (json.JSONDecodeError, ValueError, KeyError, TypeError):
			logger.info('JSON format error')

		return check, dict_from_string
	
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
				print (key , "type in dict is", type(json_dict[key]), 
					" - ", key, "type in schema is ", type(data_schema_field_types[key]))
				if type(json_dict[key]) != type(data_schema_field_types[key]):
					if (type(json_dict[key]) is str and type(data_schema_field_types[key]) is unicode) or (type(json_dict[key]) is dict and type(data_schema_field_types[key]) is 'nti.contentrendering.courseinfo.model.Enrollment'):
						matched_fields_type.append(key)
					else:
						print ("unmatched field type")
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
				print ("json file does not contain ", key)
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
			print("All required fields are available")
		else:
			print("json file is missing the following required fields:")
			print(missing_required_fields)
		json_validation_report.append(check_missing_required_fields)
		json_validation_report.append(missing_required_fields)

		#check whether the json file has missing fields compare to fields defined in the schema
		check_dict, warning_msg1, missing_fields = self.check_missing_fields(json_dict, data_schema_fields_name)
		if check_dict == False:
			print(warning_msg1)
			print(missing_fields)
		else:
			print("json file has all the schema fields")
		json_validation_report.append(check_dict)
		json_validation_report.append(warning_msg1)
		json_validation_report.append(missing_fields)

		#check whether course_info.json has additional fields not defined in the schema
		check_field_name, matched_fields, unmatched_fields, additional_field_in_dict, warning_msg2 = self.check_additional_fields(json_dict, data_schema_fields_name)
		if check_field_name == True:
			print("json file has the same fields with its schema")
		else:
			print(warning_msg2)
			print(unmatched_fields)
		json_validation_report.append(check_field_name)
		json_validation_report.append(matched_fields)
		json_validation_report.append(unmatched_fields)
		json_validation_report.append(additional_field_in_dict)
		json_validation_report.append(warning_msg2)

		#check fields type
		check_type, matched_fields_type, unmatched_fields_type = self.check_field_type(json_dict, data_schema_fields_type)
		if check_type == True:
			print("All field types in json file match with fields type in the schema")
		else:
			print ("The following fields have different types than the schema")
			print (unmatched_fields_type)
		json_validation_report.append(check_type)
		json_validation_report.append(matched_fields_type)
		json_validation_report.append(unmatched_fields_type)

		return json_validation_report


	def check_instructors(self, course_info_dict, instructor_o):
		"""
		check instructor fields
		"""
		if 'instructors' in course_info_dict.keys():
			instructor_list = course_info_dict['instructors']
			for instructor_dict in instructor_list:
				self.check_json_schema(instructor_dict, instructor_o)


	def check_prerequisites(self, course_info_dict, prerequisite_o):
		"""
		check prerequisite fields
		"""
		if 'prerequisites' in course_info_dict.keys():
			prerequisite_list = course_info_dict['prerequisites']
			for prerequisite_dict in prerequisite_list:
				self.check_json_schema(prerequisite_dict, prerequisite_o)

	def check_credit (self, course_info_dict, credit_o):
		"""
		check credit fields
		"""
		if 'credit' in course_info_dict.keys():
			credit_fields = course_info_dict['credit']
			for credit_dict in credit_fields:
				self.check_json_schema(credit_dict, credit_o)
				

	def check_enrollment_obj(self, credit_fields, enrollment_o):
		"""
		check enrollment fields
		"""
		for credit_dict in credit_fields:
			if 'enrollment' in credit_dict.keys():
				enrollment_dict = credit_dict['enrollment']
				self.check_json_schema(enrollment_dict, enrollment_o)


	

		















