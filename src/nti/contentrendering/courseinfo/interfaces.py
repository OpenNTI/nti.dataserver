#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from nti.schema.field import Bool
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine

from .schema import DateTime
from .schema import Duration

class IInstructor(interface.Interface):
	defaultphoto = ValidTextLine(title='course instructor default photo', required=False)
	username = ValidTextLine(title='course instructor username', required=False)
	userid = ValidTextLine(title='course instructor userid', required=False)
	name = ValidTextLine(title='course instructor name' , required=True)
	title = ValidTextLine(title='course instructor title', required=True)

class IPrerequisite(interface.Interface):
	id = ValidTextLine(title='prerequisite id', required=False)
	id.setTaggedValue('__external_accept_id__', True)
	
	title = ValidTextLine(title="prerequisite title", required=False)

class IEnrollment(interface.Interface):
	label = ValidTextLine(title='enrollment label', required=False)
	url = ValidTextLine(title='enrollment url', required=False)

class ICredit(interface.Interface):
	hours = Number (title='credit hours', required=False, default=0)
	enrollment = Object(IEnrollment, title='course enrollment information', required=False)

class ICourseInfo (interface.Interface):
	ntiid = ValidTextLine(title='NTIID', required=True)
	
	id = ValidTextLine(title= 'course id', required=False)
	id.setTaggedValue('__external_accept_id__', True)

	school = ValidTextLine(title='school offering the course', required=True)
	is_non_public = Bool(title='course privacy', required=False)
	term = ValidTextLine(title='term', required=False)
	startDate = DateTime(title='course start date', required=False)
	duration = Duration(title='course duration', required=False)
	isPreview = Bool (title='course preview', required=False)
	
	instructors = ListOrTuple(value_type=Object(IInstructor), 
							  title='list of course instructors', 
							  required=True)
	
	prerequisites =  ListOrTuple(value_type=Object(IPrerequisite), 
								 title='course credits', 
								 required=False)
	
	credit  = ListOrTuple(value_type=Object(ICredit), 
						  title='course credits',
						  required=False)
	
	video = ValidTextLine(title='course videp', required=False)
	title = ValidTextLine(title='course title', required=False)
	description = ValidTextLine(title='course description', required=False)
