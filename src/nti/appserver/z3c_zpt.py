#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pyramid template renderer using z3c.pt, for the path syntax
and other niceties that Chameleon itself doesn't support

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.i18n.locales import locales

from z3c.pt.pagetemplate import ViewPageTemplateFile

from pyramid.i18n import get_locale_name
from pyramid.interfaces import ITemplateRenderer
from pyramid.decorator import reify
from pyramid import renderers

def renderer_factory(info):
	"""
	Factory to produce renderers. Intended to be used with asset specs.
	"""
	return renderers.template_renderer_factory(info, ZPTTemplateRenderer)

@interface.implementer(ITemplateRenderer)
class ZPTTemplateRenderer(object):
	"""
	Renders using a :class:`z3c.pt.pagetemplate.ViewPageTemplateFile`
	"""
	def __init__(self, path, lookup):
		self.path = path
		self.lookup = lookup

	@reify # avoid looking up reload_templates before manager pushed
	def template(self):
		return ViewPageTemplateFile(self.path,
									auto_reload=self.lookup.auto_reload,
									debug=self.lookup.debug,
									translate=self.lookup.translate)

	def implementation(self):
		return self.template

	def __call__(self, value, system):
		"""
		:param value: The object returned from the view. Either a dictionary,
			or a context object. If a context object, will be available at the path
			``options/here`` in the template. If a dictionary, its values are merged with
			those in `system`.
		"""
		__traceback_info__ = value, system
		try:
			system.update(value)
		except (TypeError, ValueError):
			#raise ValueError('renderer was passed non-dictionary as value')
			system['here'] = value
			# See plasTeX/Renderers/__init__.py for comments about how 'self' is a problem
		# Compatibility with the expected Request/Response values from Zope
		request = system['request']
		request.response.getHeader = lambda k: request.response.headers[k]
		request.locale = locales.getLocale( *get_locale_name( request ).split( '-' ) )

		result = self.template.bind( system['view'] )( **system )

		return result
