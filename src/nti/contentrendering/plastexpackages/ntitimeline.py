# -*- coding: utf-8 -*-
"""
Define macros for presenting TimelineJS 

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

from zope import interface
from zope.cachedescriptors.property import readproperty

from plasTeX import Command

from ..resources.interfaces import IRepresentableContentUnit
from ..resources.interfaces import IRepresentationPreferences

from .ntilatexmacros import ntimedia

class ntitimelinename(Command):
	unicode = u'Timeline'

class ntitimeline(ntimedia):
	args = '[options:dict] title'
	blockType = True

	counter = 'ntitimeline'
	_ntiid_cache_map_name = '_timeline_ntiid_map'
	_ntiid_allow_missing_title = True
	_ntiid_suffix = 'timeline.'
	_ntiid_title_attr_name = 'title'
	_ntiid_type = 'JSON:Timeline'

	mime_type = mimeType = "application/vnd.nextthought.ntitimeline"

	suggested_height = None
	suggested_width = None
	suggested_inline = False

	@interface.implementer(IRepresentableContentUnit, IRepresentationPreferences)
	class ntitimelinesource(Command):
		args = '[options:dict] src:str:source'
		blockType = True
		resourceTypes = ( 'jsonp', )

		def invoke( self, tex ):
			result = super(ntitimeline.ntitimelinesource, self).invoke( tex )
			self.attributes['src'] = os.path.join(
				self.ownerDocument.userdata.getPath('working-dir'), self.attributes['src'])
			return result

		def digest(self, tokens):
			tok = super(ntitimeline.ntitimelinesource, self).digest(tokens)
			self.options = self.attributes.get( 'options', {} ) or {}
			return tok

	def digest(self, tokens):
		tok = super(ntitimeline,self).digest(tokens)

		self.title = self.attributes.get('title')
		self._options = self.attributes.get( 'options', {} ) or {}
		if 'suggested_height' in self._options.keys():
			self.suggested_height = self._options['suggested_height']
		if 'suggested_width' in self._options.keys():
			self.suggested_width = self._options['suggested_width']
		if 'suggested_inline' in self._options.keys():
			if self._options['suggested_inline'] in [ u'true', u'True' ]:
				self.suggested_inline = True

		return tok

	@readproperty
	def description(self):
		description = u''
		descriptions = self.getElementsByTagName('ntidescription')
		if descriptions:
			description = descriptions[0].attributes.get('content')
		return description

	@readproperty
	def icon(self):
		icon = None
		icons = self.getElementsByTagName('includegraphics')
		if icons:
			icon = icons[0]
		return icon

	@readproperty
	def uri(self):
		uri = u''
		uris = self.getElementsByTagName('ntitimelinesource')
		if uris:
			uri = uris[0].raw.url
		return uri

def ProcessOptions( options, document ):
	document.context.newcounter('ntitimeline')

from plasTeX.interfaces import IOptionAwarePythonPackage
interface.moduleProvides(IOptionAwarePythonPackage)
