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

	def implementation(self): # pragma: no cover
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


		request = PyramidZopeRequestProxy( system['request'] )
		system['request'] = request

		view = system['view']
		if view is None:
			view = request
			system['view'] = request

		result = self.template.bind( view )( **system )
		#print(result)
		return result

from zope.proxy import non_overridable
from zope.proxy.decorator import SpecificationDecoratorBase
import zope.publisher.interfaces.browser
#import zope.publisher.interfaces.http # For IHTTPResponse, should we need it
import operator

@interface.implementer(zope.publisher.interfaces.browser.IBrowserRequest)
class PyramidZopeRequestProxy(SpecificationDecoratorBase):
	"""
	Makes a Pyramid IRequest object look like a Zope request
	for purposes of rendering.

	.. note:: Most of this behaviour is added from reverse-engineering what
		existing zope code, most notably :mod:`z3c.table.table` uses.
	"""

	def __init__( self, base ):
		SpecificationDecoratorBase.__init__( self, base )
		base.response.getHeader = lambda k: base.response.headers[k]
		base.response.setHeader = lambda k, v, literal=False: operator.setitem( base.response.headers, str(k), str(v) if isinstance(v,unicode) else v )

	@non_overridable
	def get( self, key, default=None ):
		"""
		Returns GET and POST params. Multiple values are returned as lists.

		Pyramid's IRequest has a deprecated method that exposes
		the WSGI environ, making the request dict-like for the environ.
		Hence the need to mark this method non_overridable.
		"""
		def _d_o_l( o ):
			return o.dict_of_lists() if hasattr( o, 'dict_of_lists' ) else o.copy() # DummyRequest GET/POST are different
		dict_of_lists = _d_o_l( self.GET )
		dict_of_lists.update( _d_o_l( self.POST ) )
		val = dict_of_lists.get( key )
		if val:
			if len(val) == 1:
				val = val[0] # de-list things that only appeared once
		else:
			val = default
		return val

	@property
	def locale(self):
		return locales.getLocale( *get_locale_name( self ).split( '-' ) )
