#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTI course macros

$Id: slidedeckextractor.py 21266 2013-07-23 21:52:35Z sean.jones $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime
from datetime import timedelta

from plasTeX.Base import Command
from plasTeX.Base import Crossref
from plasTeX.Base import Environment
from plasTeX.Base.LaTeX.Sectioning import part
from plasTeX.Base.LaTeX.Sectioning import chapter
from plasTeX.Base.LaTeX.Sectioning import section
from plasTeX.Base.LaTeX.Sectioning import subsection
from plasTeX.Base.LaTeX.Sectioning import subsubsection

from pytz import timezone
from pytz import all_timezones

from nti.contentrendering import plastexids

DEFAULT_TZ = 'US/Central'

class coursename(Command):
	pass

class course(Environment, plastexids.NTIIDMixin):
	args = '[ options:dict ] title number'

	counter = 'course'
	blockType = True
	forcePars = False
	_ntiid_cache_map_name = '_course_ntiid_map'
	_ntiid_allow_missing_title = False
	_ntiid_suffix = 'course.'
	_ntiid_title_attr_name = 'ref'
	_ntiid_type = 'NTICourse'

	def invoke(self, tex):
		res = super(course,self).invoke(tex)
		if self.macroMode == self.MODE_BEGIN:
			self.title = self.attributes['title']
			self.number = self.attributes['number']
		return res

	def digest(self, tokens):
		tok = super(course,self).digest(tokens)
		if self.macroMode == self.MODE_BEGIN:
			if not getattr(self, 'title', ''):
				raise ValueError("Must specify a title using \\caption")

			options = self.attributes.get( 'options', {} ) or {}
			if 'tz' in options and options['tz'] in all_timezones:
				self.tz = timezone(options['tz'])
			else:
				logger.warn('No valid timezone specified')
				self.tz = timezone( DEFAULT_TZ )

			__traceback_info__ = options, self.attributes

		return tok

	class courseboard(Command):
		args = '[ options:dict ] ntiid:str'

		def digest(self, tokens):
			super(course.courseboard, self).digest(tokens)
			self.parentNode.discussion_board = self.attributes.get('ntiid')

	class courseannouncementboard(Command):
		args = '[ options:dict ] ntiid:str'

		def digest(self, tokens):
			super(course.courseannouncementboard, self).digest(tokens)
			self.parentNode.announcement_board = self.attributes.get('ntiid')

	class coursecommunity(Command):
		args = '[ options:dict ] ntiid:str'

		def digest(self, tokens):
			tok = super(course.coursecommunity,self).digest(tokens)

			options = self.attributes.get( 'options', {} ) or {}
			if 'scope' in options:
				self.scope = options['scope']
			else:
				self.scope = u'public'

			__traceback_info__ = options, self.attributes

			return tok


class courseunitname(Command):
	pass

class courseunit(Environment, plastexids.NTIIDMixin):
	args = '[ options:dict ] title:str'

	counter = "courseunit"
	blockType = True
	forcePars = False
	_ntiid_cache_map_name = '_courseunit_ntiid_map'
	_ntiid_allow_missing_title = False
	_ntiid_suffix = 'course.unit.'
	_ntiid_title_attr_name = 'ref'
	_ntiid_type = 'NTICourseUnit'

	def invoke(self, tex):
		res = super(courseunit,self).invoke(tex)
		if self.macroMode == self.MODE_BEGIN:
			self.title = self.attributes['title']
		return res

	def digest(self, tokens):
		res = super(courseunit,self).digest(tokens)
		if self.macroMode == self.MODE_BEGIN:
			if not getattr(self, 'title', ''):
				raise ValueError("Must specify a title using \\caption")

			options = self.attributes.get( 'options', {} ) or {}
			__traceback_info__ = options, self.attributes

		return res

class courselessonname(Command):
	pass

class courselessonref(Crossref.ref):
	args = 'label:idref {date:str}'

	date = ()

	def invoke( self, tex ):
		res = super(courselessonref, self).invoke( tex )
		if self.attributes.get('date'):
			__traceback_info__ = self.attributes['date']
			dates = self.attributes['date'].split(',')
			self.date = []
			for date in dates:
				if date:
					date = date.split('/')
					# FIXME: Non-standard date representation
					self.date.append(datetime(int(date[2]), int(date[0]), int(date[1])))
				else:
					self.date.append(datetime.today())
			self.date[-1] = self.date[-1] + timedelta(days=1) - timedelta(microseconds=1)
		return res

class coursepart(part):
	counter = 'course' + part.counter

class courselesson(chapter):
	args = '* [ toc ] title label:id'
	blockType = True
	counter = 'courselesson'
	forcePars = False

class courselessonsection(section):
	counter = 'course' + section.counter

class courselessonsubsection(subsection):
	counter = 'course' + subsection.counter

class courselessonsubsubsection(subsubsection):
	counter = 'course' + subsubsection.counter

class courseinfoname(Command):
	pass

class courseinfo(section):
	args = '* [ toc ] title'
	blockType = True
	counter = 'courseinfo'
	forcePars = False

def ProcessOptions( options, document ):
	document.context.newcounter('course')
	document.context.newcounter('courseinfo')
	document.context.newcounter('courseunit')

	for counter_cls in courseunit, coursepart, courselesson, courselessonsection, courselessonsubsection, courselessonsubsubsection:
		document.context.newcounter(counter_cls.counter)


from plasTeX.interfaces import IOptionAwarePythonPackage
from zope import interface
interface.moduleProvides(IOptionAwarePythonPackage)
