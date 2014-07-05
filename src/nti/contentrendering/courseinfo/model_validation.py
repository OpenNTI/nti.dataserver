#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


import simplejson as json
from . import model
from . import interfaces

import zope.schema
from collections import OrderedDict

class CourseInfoJSONChecker(object):

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
				#print (name, type(data_schema_fields_type[name]), field.required)
		return data_schema_fields_name, data_schema_fields_type, data_schema_fields_required


	def get_dict_from_file(self, file_name):
		"""
		Read course_info.json file
		Transform its content into python object and check if the json sytax is valid
		Return course_info.json in the form of python object (course_info_dict)
		"""

		f = open(file_name, 'r')
		file_content = f.read()
		try:
			dict_from_string = json.loads(file_content)
			return dict_from_string
		except (json.JSONDecodeError, ValueError, KeyError, TypeError):
			raise


	def set_unmatched_fields(self, unmatched_fields):
		"""
		Save list of unmatched fields between course_info dict and course_info schema
		"""
		self.unmatched_fields = unmatched_fields

	def get_unmatched_fields(self):
		"""
		Get list of unmatched fields between course_info dict and course_info schema
		"""
		return self.unmatched_fields

	def get_value_of_a_field (self, key_name, json_dict):
		"""
		Return a value of a particular key from course_info dict
		"""
		return json_dict[key_name]


	def check_missing_fields(self, json_dict, data_schema_fields):
		"""
		check whether json_dict (obtained from course_info.json) has missing fields
		"""
		check = False
		warning_msg = ''
		missing_fields = self.find_unmatched_fields(data_schema_fields, json_dict.keys())
		if len(missing_fields) > 0:
			check = False
			warning_msg = 'course_info.json has some missing fields compare to courseinfo schema'
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
			warning_msg = 'course_info.json contains more fields than defined courseinfo schema'
		else:
			matched_fields = self.find_matched_fields(json_dict.keys(), data_schema_fields)
			unmatched_fields = self.find_unmatched_fields(json_dict.keys(), matched_fields)
			if len(unmatched_fields) == 0:
				#course_info.json has all fields defined in course_info schema
				check = True
			elif len(unmatched_fields) > 0:
				check = False
				warning_msg = 'course_info.json contains fields not defined in courseinfo schema'

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
				if type(json_dict[key]) != type(data_schema_field_types[key]):
					if type(json_dict[key]) is str and type(data_schema_field_types[key]) is unicode:
						#print ("unmatched but it is ok")
						matched_fields_type.append(key)
					else:
						#print ("unmatched field type")
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
				#print ("json file does not contain ", key)
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
