#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTI course macros

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime
from datetime import timedelta

import pytz

from plasTeX import Command
from plasTeX import Environment
from plasTeX.Base.LaTeX.Crossref import ref
from plasTeX.Base.LaTeX.Sectioning import part
from plasTeX.Base.LaTeX.Sectioning import chapter
from plasTeX.Base.LaTeX.Sectioning import section
from plasTeX.Base.LaTeX.Sectioning import subsection
from plasTeX.Base.LaTeX.Sectioning import subsubsection

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
	tz = None

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
			if 'tz' in options:
				# Blow up if the user gave us a bad timezone, rather
				# then silently producing the wrong output
				self.tz = pytz.timezone(options['tz'])
				logger.warn('tz option is deprecated, use nti_render_conf.ini')
				self.ownerDocument.userdata['document_timezone_name'] = options['tz']
			else:
				logger.warn('No valid timezone specified')
				self.tz = pytz.timezone( DEFAULT_TZ )
				self.ownerDocument.userdata['document_timezone_name'] = DEFAULT_TZ

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

from nti.externalization.datetime import datetime_from_string

def _parse_local_date(self, val):
	# If they gave no timezone information,
	# use the document's
	return datetime_from_string( val,
								 assume_local=True,
								 local_tzname=self.ownerDocument.userdata.get('document_timezone_name') )

class coursepartname(Command):
	pass

class coursepart(part):
	counter = 'course' + part.counter

class courselessonref(ref):
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
					if '/' in date:
						date = date.split('/')
						# FIXME: Non-standard date representation
						iso_date = '%s-%s-%s' % (date[2], date[0], date[1])
						logger.info("Interpreting %s to mean %s in ISO format (YYYY-MM-DD)", 
									date, iso_date)
						date = iso_date
					if 'T' not in date:
						date += 'T00:00'
					self.date.append(_parse_local_date(self, date))
				else:
					self.date.append(datetime.today())
			self.date[-1] = self.date[-1] + timedelta(days=1) - timedelta(microseconds=1)
		return res

class courselessonname(Command):
	pass

class courselesson(chapter):
	args = '* [ toc ] title label:id {options:dict:str}' # TODO: Move towards dates at this level
	blockType = True
	counter = 'courselesson'
	forcePars = False

	is_outline_stub_only = None

def _parse_date_at_invoke(self):
	# FIXME: We want these to be relative, not absolute, so they
	# can be made absolute based on when the course begins.
	# How to represent that? Probably need some schema transformation
	# step in nti.externalization? Or some auixilliary data fields?
	options = self.attributes.get('options') or ()
	def _parse(key, default_time):
		if key in options:
			val = options[key]
			if 'T' not in val:
				# If they give no timestamp, make it default_time
				val += default_time
			# Now parse it.
			return _parse_local_date(self, val)

	not_before = _parse('not_before_date', 'T00:00')
	not_after = _parse('not_after_date', 'T23:59')

	if not_before is not None and not_after is not None:
		# Both are required.
		# TODO: Check sequence.
		return not_before, not_after
	# For compatibility with \courselessonref, we also accept just the ending
	# date.
	if not_after is not None:
		return (not_after,)

	return ()

from paste.deploy.converters import asbool

def _parse_isoutline_at_invoke(self):
	options = self.attributes.get('options')
	if options and 'is_outline_stub_only' in options:
		return asbool(options.get('is_outline_stub_only'))

def _make_invoke(cls):
	def invoke(self, tex):
		res = super(cls, self).invoke(tex)
		self.date = _parse_date_at_invoke(self)
		self.is_outline_stub_only = _parse_isoutline_at_invoke(self)
		return res
	return invoke

class courselessonsectionname(Command):
	pass

class courselessonsection(section):
	"""
	Example::

		\courselessonsection{Title}{not_after_date=2014-01-13}

	"""
	counter = 'course' + section.counter
	args = '* [ toc ] title {options:dict:str}'

	is_outline_stub_only = None

class courselessonsubsectionname(Command):
	pass

class courselessonsubsection(subsection):
	"""
	Example::

		\courselessonsubsection{Title}{not_after_date=2014-01-13}

	"""

	counter = 'course' + subsection.counter
	args = '* [ toc ] title {options:dict:str}'

	is_outline_stub_only = None

class courselessonsubsubsectionname(Command):
	pass

class courselessonsubsubsection(subsubsection):
	"""
	Example::

		\courselessonsubsubsection{Title}{not_after_date=2014-01-13}

	"""
	counter = 'course' + subsubsection.counter
	args = '* [ toc ] title {options:dict:str}'

	is_outline_stub_only = None

for _c in (courselesson, courselessonsection, courselessonsubsection,
		   courselessonsubsubsection):
	_c.invoke = _make_invoke(_c)

class courseinfoname(Command):
	pass

class courseinfo(section):
	args = '* [ toc ] title'
	blockType = True
	counter = 'courseinfo'
	forcePars = False

class courseoverviewgroupname(Command):
	pass

class courseoverviewgroup(Environment):
	"""
	Data structure to organize a 'lessons' resources on the overview page. 
	If the content author does not sepecify and overview groups, then the
	resources will be grouped by resource type.
	"""
	args = '[ options:dict ] <title>'
	blockType = True
	forcePars = False
	counter = 'courseoverviewgroup'

	mime_type = "application/vnd.nextthought.nticourseoverviewgroup"

	class titlebackgroundcolor(Command):
		"""
		Sets the background color of the overview title bar.
		This should be specified in hex.
		"""
		args = 'color:string'

		def digest(self, tokens):
			super(courseoverviewgroup.titlebackgroundcolor, self).digest(tokens)

			self.parentNode.title_background_color = self.attributes.get('color')

class courseoverviewspacer(Command):
	mime_type = "application/vnd.nextthought.nticourseoverviewspacer"

def ProcessOptions( options, document ):
	for counter_cls in (course, courseinfo, courseunit, coursepart, courselesson,
						courselessonsection, courselessonsubsection,
						courselessonsubsubsection, courseoverviewgroup):
		document.context.newcounter(counter_cls.counter)

from zope import interface

from plasTeX.interfaces import IOptionAwarePythonPackage
interface.moduleProvides(IOptionAwarePythonPackage)
