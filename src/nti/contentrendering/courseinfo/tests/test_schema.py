#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import isodate

from nti.externalization import internalization
from nti.externalization.externalization import toExternalObject
from nti.externalization.tests import assert_does_not_pickle
does_not = is_not

from nti.contentrendering.courseinfo import model
from nti.contentrendering.courseinfo import interfaces

from nti.testing.matchers import verifiably_provides

from . import CourseinfoLayerTest


import zope.schema
from collections import OrderedDict

class TestCourseInfo(CourseinfoLayerTest):

	def test_instructor_object(self):
		io = model.Instructor(defaultphoto="images/Morvant.png", username="morv1533",
							  name="Mark Morvant, PhD", title="Professor, Department of Chemistry")
		out = OrderedDict()
		# Check all interfaces provided by the object
		ifaces = io.__provides__.__iro__
		# Check fields from all interfaces
		for iface in ifaces:
			fields = zope.schema.getFieldsInOrder(iface)
			for name, field in fields:
				out[name] = getattr(io, name, None)




		assert_that (io, verifiably_provides(interfaces.IInstructor))
		assert_does_not_pickle(io)

		assert_that(io, has_property('name', is_('Mark Morvant, PhD')))

		ext_obj = toExternalObject(io)

		assert_that(ext_obj, has_entry('Class', 'Instructor'))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
	 	assert_that(new_io, has_property('defaultphoto', is_('images/Morvant.png')))
		assert_that(new_io, has_property('username', is_('morv1533')))
		assert_that(new_io, has_property('name', is_('Mark Morvant, PhD')))
		assert_that(new_io, has_property('title', is_('Professor, Department of Chemistry')))

	def test_prerequisite_object(self):
		io = model.Prerequisite(id="CHEM 3000-001", title="Senior standing or instructor permission")
		out = OrderedDict();
		# Check all interfaces provided by the object
		assert_that(io, verifiably_provides(interfaces.IPrerequisite))
		assert_does_not_pickle(io)

		ext_obj = toExternalObject(io)

		assert_that(ext_obj, has_entry('Class', 'Prerequisite'))
		assert_that(ext_obj, has_entry('ID', is_('CHEM 3000-001')))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('id', is_('CHEM 3000-001')))
		assert_that(new_io, has_property('title', is_('Senior standing or instructor permission')))


	def test_enrollment_object(self):
		io = model.Enrollment(label="Enroll with Ozone", url="http://ozone.ou.edu/")
		out = OrderedDict();
		# Check all interfaces provided by the object
		assert_that (io, verifiably_provides(interfaces.IEnrollment))
		assert_does_not_pickle(io)


		ext_obj = toExternalObject(io)

		assert_that(ext_obj, has_entry('Class', 'Enrollment'))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('label', is_('Enroll with Ozone')))
		assert_that(new_io, has_property('url', is_('http://ozone.ou.edu/')))


	def test_credit_object(self):
		enrollment_o = model.Enrollment(label="Enroll with Ozone", url="http://ozone.ou.edu/")

		io = model.Credit(hours=1, enrollment=enrollment_o)
		out = OrderedDict();
		# Check all interfaces provided by the object
		assert_that (io, verifiably_provides(interfaces.ICredit))
		assert_does_not_pickle(io)

		ext_obj = toExternalObject(io)

		assert_that(ext_obj, has_entry('Class', 'Credit'))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('hours', is_(1)))
		assert_that(new_io, has_property('enrollment', is_(enrollment_o)))



	def test_course_info_object (self):
		prerequisite_o = model.Prerequisite(id="CHEM 3000-001", title="Senior standing or instructor permission")
		enrollment_o = model.Enrollment(label="Enroll with Ozone", url="http://ozone.ou.edu/")
		credit_o = model.Credit(hours=1, enrollment=enrollment_o)
		instructor1 = model.Instructor(defaultphoto="images/Morvant.png", username="morv1533",
			name="Mark Morvant, PhD", title="Professor, Department of Chemistry")
		instructor2 = model.Instructor(defaultphoto="images/Sims.png", username="sims2543",
			name="Paul Sims, PhD", title="Associate Professor, Department of Chemistry")

		io = model.CourseInfo(ntiid="tag:nextthought.com,2011-10:OU-HTML-CHEM4970_Chemistry_of_Beer.course_info",
			id="CHEM 4970-001", school="Department of Chemistry and Biochemistry at the University of Oklahoma",
			is_non_public=False, term="Fall 2014", startDate=isodate.parse_datetime("2014-01-13T06:00:00+00:00"), duration="16 Weeks",
			isPreview=True, instructors=[instructor1, instructor2],
			video= "kaltura://1500101/0_bxfatwxs/",
			title="Chemistry of Beer",
			description="This course covers the process of brewing from grain to final bottle product and the chemical and biochemical process involved in each step. Students will be required to utilize previous knowledge in General and Organic chemistry to understand: analytical techniques in brewing, chemistry of the ingredients and products, and the molecules involved in the biochemical processes.  During the course, students will also learn the similarities and differences between beer styles, home and commercial brewing processes, and analytical techniques.  There is a great deal of Biochemistry and Organic Chemistry involved in the malting, mashing and fermentation process and understanding the chemistry behind the flavor, aroma, and color of beer. Students should have a basic knowledge of general and organic chemistry.",
			credit=[credit_o],
			prerequisites=[prerequisite_o]
			)



		# Check all interfaces provided by the object
		ifaces = io.__provides__.__iro__

		# Check fields from all interfaces
		out = OrderedDict()
		field_list = []
		for iface in ifaces:
			fields = zope.schema.getFieldsInOrder(iface)
			for name, field in fields:
				out[name] = getattr(io, name, None)

				field_list.append(name)


		assert_that(io, verifiably_provides(interfaces.ICourseInfo))
		assert_does_not_pickle(io)

		ext_obj = toExternalObject(io)
		assert_that(ext_obj, has_entry('Class', 'CourseInfo'))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()

		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('ntiid', is_('tag:nextthought.com,2011-10:OU-HTML-CHEM4970_Chemistry_of_Beer.course_info')))
		assert_that(new_io, has_property('id', is_('CHEM 4970-001')))
		assert_that(new_io, has_property('school', is_('Department of Chemistry and Biochemistry at the University of Oklahoma')))
		assert_that(new_io, has_property('is_non_public', is_(False)))
		assert_that(new_io, has_property('term', is_('Fall 2014')))
		assert_that(new_io, has_property('startDate', is_not(none())))
		assert_that(new_io, has_property('duration', is_('16 Weeks')))
		assert_that(new_io, has_property('isPreview', is_(True)))
		assert_that(new_io, has_property('instructors', is_([instructor1, instructor2])))
		assert_that(new_io, has_property('prerequisites', is_([prerequisite_o])))
		assert_that(new_io, has_property('credit', is_([credit_o])))
		assert_that(new_io, has_property('video', is_('kaltura://1500101/0_bxfatwxs/')))
		assert_that(new_io, has_property('title', is_('Chemistry of Beer')))
		assert_that(new_io, has_property('description', is_('This course covers the process of brewing from grain to final bottle product and the chemical and biochemical process involved in each step. Students will be required to utilize previous knowledge in General and Organic chemistry to understand: analytical techniques in brewing, chemistry of the ingredients and products, and the molecules involved in the biochemical processes.  During the course, students will also learn the similarities and differences between beer styles, home and commercial brewing processes, and analytical techniques.  There is a great deal of Biochemistry and Organic Chemistry involved in the malting, mashing and fermentation process and understanding the chemistry behind the flavor, aroma, and color of beer. Students should have a basic knowledge of general and organic chemistry.')))
