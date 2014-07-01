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

class TestCourseInfoValidation():
	def build_sample_course_info_schema(self):
		self.prerequisite_o = model.Prerequisite(id = "CHEM 3000-001", title="Senior standing or instructor permission")
		self.enrollment_o = model.Enrollment(label = "Enroll with Ozone", url = "http://ozone.ou.edu/")
		self.credit_o = model.Credit(hours = 1, enrollment = self.enrollment_o)
		self.instructor1 = model.Instructor(defaultphoto = "images/Morvant.png", username = "morv1533", 
			name = "Mark Morvant, PhD", title = "Professor, Department of Chemistry")
		self.instructor2 = model.Instructor(defaultphoto = "images/Sims.png", username = "sims2543",
			name = "Paul Sims, PhD", title = "Associate Professor, Department of Chemistry")
		self.course_info_schema = model.CourseInfo(ntiid = "tag:nextthought.com,2011-10:OU-HTML-CHEM4970_Chemistry_of_Beer.course_info",
			id = "CHEM 4970-001", school = "Department of Chemistry and Biochemistry at the University of Oklahoma",
			is_non_public = False, term = "Fall 2014", startDate = "2014-01-13T06:00:00+00:00", duration = "16 Weeks",
			isPreview = True, instructors = [self.instructor1, self.instructor2], 
			video =  "kaltura://1500101/0_bxfatwxs/",
			title = "Chemistry of Beer",
			description = "This course covers the process of brewing from grain to final bottle product and the chemical and biochemical process involved in each step. Students will be required to utilize previous knowledge in General and Organic chemistry to understand: analytical techniques in brewing, chemistry of the ingredients and products, and the molecules involved in the biochemical processes.  During the course, students will also learn the similarities and differences between beer styles, home and commercial brewing processes, and analytical techniques.  There is a great deal of Biochemistry and Organic Chemistry involved in the malting, mashing and fermentation process and understanding the chemistry behind the flavor, aroma, and color of beer. Students should have a basic knowledge of general and organic chemistry.",
			credit = [self.credit_o],
			prerequisites = [self.prerequisite_o]
			)

	def check_course_instructors(self, course_info, course_info_dict):
		#check instructors listed in the course_info.json
		course_info.check_instructors(course_info_dict, self.instructor1)


	def check_course_prerequisites(self, course_info, course_info_dict):
		#check prerequisites listed in the course_info.json
		course_info.check_prerequisites(course_info_dict, self.prerequisite_o)

	def check_course_credit(self, course_info, course_info_dict):
		#check credit listed in course_info.json
		course_info.check_credit(course_info_dict, self.credit_o)

	def check_course_enrollment(self, course_info, credit_fields):
		#check enrollment information listed course_info.json
		course_info.check_enrollment_obj(credit_fields, self.enrollment_o)


	def test_course_info_validation(self):
		self.build_sample_course_info_schema()
		course_info_file = '/Users/ega/Projects/AoPSBooks5/CHEM4970_Chemistry_of_Beer/Templates/Themes/Generic/course_info.json'
		course_info = course_info_validation.CourseInfoJSONChecker(self.course_info_schema, course_info_file)
		check_json_syntax, course_info_dict= course_info.get_dict_from_file(course_info.file_name)
		if course_info_dict!= None:		
			
			#check course_info.json based on its schema
			course_info.check_json_schema(course_info_dict, self.course_info_schema)

			#check value of particular fields in course_info_dict
			
			#make sure that ntiid fields in course_info.json ends with 'course_info'
			check = course_info.check_ntiid_value (course_info_dict, 'course_info')
			if check == True :
				print ("ntiid value ends with string 'course_info'")
			elif check == False:
				print("invalid ntiid value")
			else:
				print("there is no ntiid field in the dictionary")


			#check course duration field
			duration_number, duration_kind, duration_days = course_info.check_duration(course_info_dict)
			print("Course duration is ",duration_kind," is ",duration_number)
			print("Course duration in days is ", duration_days)

			#check course instructors field
			print("-------------------------------------------------------")
			print ("Check Instructors")
			self.check_course_instructors(course_info, course_info_dict)

			#check course prerequisites field
			print("-------------------------------------------------------")
			print ("Check Prerequisites")
			self.check_course_prerequisites(course_info, course_info_dict)

			#check course credit field
			print("-------------------------------------------------------")
			print("Check Credit")
			self.check_course_credit(course_info, course_info_dict)

			#check course enrollment field
			print("-------------------------------------------------------")
			print("Check Enrollment Information")
			if 'credit' in course_info_dict.keys():
				credit_fields = course_info_dict['credit']
				self.check_course_enrollment(course_info, credit_fields)

		else:
			print("JSON Format Error")

print ("start checking")
check = TestCourseInfoValidation()
check.test_course_info_validation()

