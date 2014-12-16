#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helpers and utilities used for implementing other parts of the packages.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.cachedescriptors.property import readproperty

from plasTeX.Renderers import render_children

from nti.contentfragments.interfaces import HTMLContentFragment
from nti.contentfragments.interfaces import ILatexContentFragment
from nti.contentfragments.interfaces import IPlainTextContentFragment

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
	# We are doing an interface conversion here, because
	# getting the unicode may be unescaping and we need to escap
	# again (?)
	return ILatexContentFragment(''.join(output).strip())

def _is_renderable(renderer, elements):
	"""
	quick test to find out if elements are renderable
	"""
	result = bool(renderer is not None and elements)
	if result:
		for element in elements:
			result = hasattr(element, 'nodeType') and \
					 hasattr(element, 'unicode')  and \
					 hasattr(element, 'nodeName') and \
					 hasattr(element, 'attributes') and \
					 hasattr(element, 'filename')
			if not result:
				break
	return result
	
def _htmlcontent_rendered_elements(renderer, elements):
	output = render_children(renderer, elements)
	# Now return an actual HTML content fragment. Note that this
	# has been rendered so there's no need to do the interface
	# conversion
	result = HTMLContentFragment(''.join(output).strip())
	return result

def _textcontent_rendered_elements(renderer, elements):
	content = _htmlcontent_rendered_elements(renderer, elements)
	text = component.getAdapter(content, IPlainTextContentFragment, name='text')
	return text

def _asm_rendered_textcontent(self, ignorable_renderables=()):
	"""
	Collects the rendered values of the children of self. Can only be used
	while in the rendering process. Returns a `unicode` object.

	:keyword ignorable_renderables: If given, a tuple (yes, tuple)
		of classes. If a given child node is an instance of a
		class in the tuple, it will be ignored and not rendered.
	"""

	if not ignorable_renderables:
		selected_children = self.childNodes
	else:
		selected_children = \
			tuple(node for node in self.childNodes \
			 	  if not isinstance(node, ignorable_renderables))

	result = _htmlcontent_rendered_elements(self.renderer, selected_children)
	return result

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

	Mixin order matters, this needs to be first; if you override
	``_after_render`` you must be sure to call this implementation of it.
	"""

	_asm_ignorable_renderables = ()

	#: Starts out as the non-rendered latex source fragment
	#: of the children of this node, ignoring things defined in
	#: _asm_ignorable_renderables; after this object
	#: has been rendered, replaced with their HTML content.
	_asm_local_content = readproperty(_asm_local_textcontent)

	def _after_render(self, rendered):
		self._asm_local_content = _asm_rendered_textcontent(self, self._asm_ignorable_renderables)
