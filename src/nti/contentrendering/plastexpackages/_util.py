#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helpers and utilities used for implementing other parts of the packages.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope.cachedescriptors.property import readproperty

from nti.contentfragments import interfaces as cfg_interfaces
from plasTeX.Renderers import render_children

def _asm_local_textcontent(self):
	"""
	Collects the text content for nodes that are direct
	children of `self`, *not* recursively. Returns a `unicode` object,
	*not* a :class:`plasTeX.DOM.Text` object.
	"""
	output = []
	for item in self.childNodes:
		if item.nodeType == self.TEXT_NODE:
			output.append(unicode(item))
		elif getattr(item, 'unicode', None) is not None:
			output.append(item.unicode)
	return cfg_interfaces.ILatexContentFragment( ''.join( output ).strip() )

def _asm_rendered_textcontent(self, ignorable_renderables=()):
	"""
	Collects the rendered values of the children of self. Can only be used
	while in the rendering process. Returns a `unicode` object.
	"""
	childNodes = []
	for item in self.childNodes:
		if isinstance(item, ignorable_renderables):
			continue
		childNodes.append( item )

	output = render_children( self.renderer, childNodes )
	return cfg_interfaces.HTMLContentFragment( ''.join( output ).strip() )

class LocalContentMixin(object):
	"""
	Something that can collect local content. Defines one property,
	`_asm_local_content` to be the value of the local content. If this
	object has never been through the rendering pipline, this will be
	a LaTeX fragment (probably with missing information and mostly
	useful for debuging). If this object has been rendered, then it
	will be an HTML content fragment according to the templates. If
	the property ``_asm_ignorable_renderables`` is defined, it is a
	tuple of classes of potential child elements that are not included
	in the rendered content.

	Mixin order matters, this needs to be first.
	"""

	_asm_ignorable_renderables = ()
	_asm_local_content = readproperty(_asm_local_textcontent)
	def _after_render( self, rendered ):
		self._asm_local_content = _asm_rendered_textcontent( self, self._asm_ignorable_renderables )
