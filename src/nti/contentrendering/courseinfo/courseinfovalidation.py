#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validate course_info.json and schema.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson as json
#import validictory # XXX: DO NOT ADD THIS DEPENDENCY


def main():
	#read json schema from file
	#check if string read from json schema file has valid syntax
	#convert json format into python obj

	fschema = open ('/Users/ega/Desktop/JSON Validator/course_info_schema.json', 'r')
	schema_string = fschema.read()
	schema_python_obj = json.loads(schema_string)
	print ("schema_python_obj type is ", type(schema_python_obj) )
	print (schema_python_obj)


	#read data in json format from file
	#check if string read from json schema file has valid syntax
	#convert json format into python obj
	fdata = open ('/Users/ega/Desktop/JSON Validator/course_info.json', 'r')
	data_string = fdata.read()
	data_python = json.loads(data_string)
	print ("data_python type is ",type(data_python))

	#validate data whether they conform with the schema
	print("Data and Schema Validation")
	try:
		validictory.validate(data_python, schema_python_obj)
		check = 1
	except ValueError, error:
		print(error)

	if check == 1:
		print("JSON file conforms with its schema")

if __name__ == '__main__':
	main()
