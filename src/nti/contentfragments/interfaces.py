#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces for working with content fragments.


$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope.mimetype import types as mime_types
mime_types.setup() # register interface classes and utilities if not already

def _setup():
	from pkg_resources import resource_filename
	types_data = resource_filename( 'nti.contentfragments', "types.csv")
	# Hmm. So this registers things in the zope.mimetype.types module
	# The ZCML directive registers them in the specified module (I think)
	# But we can't use that directive because we need them now in order to
	# implement them.
	data = mime_types.read( types_data )
	ifs = mime_types.getInterfaces( data )
	mime_types.registerUtilities( ifs, data )

_setup()

class IContentFragment(interface.Interface):
	"""
	Base interface representing different formats that content can
	be in.
	"""

from zope.interface.common import sequence

class IUnicodeContentFragment(IContentFragment,sequence.IReadSequence):
	"""
	Content represented as a unicode string.

	Although it is simplest to subclass :class:`unicode`, that is not required.
	At a minimum, what is required are the `__getitem__` method (and others
	declared by :class:`IReadSequence`), plus the `encode` method.

	"""

@interface.implementer(IUnicodeContentFragment)
class UnicodeContentFragment(unicode):
	pass

class ILatexContentFragment(IUnicodeContentFragment, mime_types.IContentTypeTextLatex):
	"""
	Interface representing content in LaTeX format.
	"""

@interface.implementer(ILatexContentFragment)
class LatexContentFragment(UnicodeContentFragment):
	pass


class IHTMLContentFragment(IUnicodeContentFragment, mime_types.IContentTypeTextHtml):
	"""
	Interface representing content in HTML format.
	"""

@interface.implementer(IHTMLContentFragment)
class HTMLContentFragment(UnicodeContentFragment):
	pass

class IPlainTextContentFragment(IUnicodeContentFragment,mime_types.IContentTypeTextPlain):
	"""
	Interface representing content in plain text format.
	"""

@interface.implementer(IPlainTextContentFragment)
class PlainTextContentFragment(UnicodeContentFragment):
	pass
