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
	args = '* [ toc ] title label:id {options:dict:str}' # TODO: Move towards dates at this level
	blockType = True
	counter = 'courselesson'
	forcePars = False

	is_outline_stub_only = False

import isodate

def _parse_date_at_invoke(self):
	# FIXME: We want these to be relative, not absolute, so they
	# can be made absolute based on when the course begins.
	# How to represent that? Probably need some schema transformation
	# step in nti.externalization? Or some auixilliary data fields?
	options = self.attributes.get('options') or ()
	def _parse(key):
		if key in options:
			val = options[key]
			if 'T' not in val:
				# If they give no timestamp, make it midnight
				val += 'T00:00'
			return isodate.parse_datetime(val)

	not_before = _parse('not_before_date')
	not_after = _parse('not_after_date')

	if not_before is not None and not_after is not None:
		# Both are required.
		# TODO: Check sequence.
		return not_before, not_after
	# For compatibility with \courselessonref, we also accept just the ending
	# date.
	if not_after is not None:
		return (not_after,)

	return ()

def _parse_isoutline_at_invoke(self):
	options = self.attributes.get('options') or ()
	if 'is_outline_stub_only' in options:
		return options['is_outline_stub_only'] == 'true'
	return False

def _make_invoke(cls):
	def invoke(self, tex):
		res = super(cls, self).invoke(tex)
		self.date = _parse_date_at_invoke(self)
		self.is_outline_stub_only = _parse_isoutline_at_invoke(self)
		return res
	return invoke

class courselessonsection(section):
	"""
	Example::

		\courselessonsection{Title}{not_after_date=2014-01-13}

	"""
	counter = 'course' + section.counter
	args = '* [ toc ] title {options:dict:str}'

	is_outline_stub_only = False

class courselessonsubsection(subsection):
	"""
	Example::

		\courselessonsubsection{Title}{not_after_date=2014-01-13}

	"""

	counter = 'course' + subsection.counter
	args = '* [ toc ] title {options:dict:str}'

	is_outline_stub_only = False

class courselessonsubsubsection(subsubsection):
	"""
	Example::

		\courselessonsubsubsection{Title}{not_after_date=2014-01-13}

	"""
	counter = 'course' + subsubsection.counter
	args = '* [ toc ] title {options:dict:str}'

	is_outline_stub_only = False

for _c in courselesson, courselessonsection, courselessonsubsection, courselessonsubsubsection:
	_c.invoke = _make_invoke(_c)

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
