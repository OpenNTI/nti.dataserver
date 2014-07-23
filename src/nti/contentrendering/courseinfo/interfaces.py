#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.schema import vocabulary

from nti.ntiids.schema import ValidNTIID

from nti.schema.field import Int
from nti.schema.field import Bool
from nti.schema.field import Choice
from nti.schema.field import Object
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import UniqueIterable

from .schema import DateTime
from .schema import Duration

DAYS = ('M', 'T' ,'W', 'R', 'F', 'S', 'N')
DAYS_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in DAYS])

class ISchedule(interface.Interface):
	days = UniqueIterable(value_type=Choice(vocabulary=DAYS_VOCABULARY, title=u'day'),
						  required=False)
	times = ListOrTuple(value_type=ValidTextLine(title=u"time-slot"), required=False)
		
class IInstructor(interface.Interface):
	defaultphoto = ValidTextLine(title=u'course instructor default photo', required=False)
	username = ValidTextLine(title=u'course instructor username', required=False)
	userid = ValidTextLine(title=u'course instructor userid', required=False)
	name = ValidTextLine(title=u'course instructor name' , required=True)
	title = ValidTextLine(title=u'course instructor title', required=True)

class IPrerequisite(interface.Interface):
	id = ValidTextLine(title=u'prerequisite id', required=False)
	id.setTaggedValue('__external_accept_id__', True)
	
	title = ValidTextLine(title=u"prerequisite title", required=False)

class IEnrollment(interface.Interface):
	label = ValidTextLine(title=u'enrollment label', required=False)
	url = ValidTextLine(title=u'enrollment url', required=False)

class ICredit(interface.Interface):
	hours = Int(title=u'credit hours', required=False, default=0, min=0)
	enrollment = Object(IEnrollment, title=u'course enrollment information', required=False)

class ICourseInfo (interface.Interface):
	ntiid = ValidNTIID(title=u'NTIID', required=True)
	
	id = ValidTextLine(title= 'course id', required=False)
	id.setTaggedValue('__external_accept_id__', True)

	school = ValidTextLine(title=u'school offering the course', required=True)
	is_non_public = Bool(title=u'course privacy', required=False)
	term = ValidTextLine(title=u'term', required=False)
	startDate = DateTime(title=u'course start date', required=False)
	duration = Duration(title=u'course duration', required=False)
	schedule = Object(ISchedule, title=u"course schedule", required=False)
	isPreview = Bool (title=u'course preview', required=False)
	
	instructors = ListOrTuple(value_type=Object(IInstructor), 
							  title=u'list of course instructors', 
							  required=True)
	
	prerequisites =  ListOrTuple(value_type=Object(IPrerequisite), 
								 title=u'course credits', 
								 required=False)
	
	credit  = ListOrTuple(value_type=Object(ICredit), 
						  title=u'course credits',
						  required=False)
	
	video = ValidTextLine(title=u'course videp', required=False)
	title = ValidTextLine(title=u'course title', required=False)
	description = ValidTextLine(title=u'course description', required=False)
