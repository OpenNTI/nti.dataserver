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
	"""
	Subclasses should override the :meth:`__add__` method
	to return objects that implement the appropriate (most derived, generally)
	interface.
	"""

	def __rmul__( self, times ):
		result = unicode.__rmul__( self, times )
		if result is not self:
			result = self.__class__( result )
		return result

	def __mul__( self, times ):
		result = unicode.__mul__( self, times )
		if result is not self:
			result = self.__class__( result )
		return result


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

###
# NOTE The implementations of the add methods go directly to
# unicode and not up the super() chain to avoid as many extra
# copies as possible
###

@interface.implementer(IHTMLContentFragment)
class HTMLContentFragment(UnicodeContentFragment):
	def __add__( self, other ):
		result = unicode.__add__( self, other )
		if IHTMLContentFragment.providedBy( other ):
			result = HTMLContentFragment( result )
		# TODO: What about the rules for the other types?
		return result



class ISanitizedHTMLContentFragment(IHTMLContentFragment):
	"""
	HTML content, typically of unknown or untrusted provenance,
	that has been sanitized for "safe" presentation in a generic,
	also unknown browsing context.
	Typically this will mean that certain unsafe constructs, such
	as <script> tags have been removed.
	"""

@interface.implementer(ISanitizedHTMLContentFragment)
class SanitizedHTMLContentFragment(HTMLContentFragment):

	def __add__( self, other ):
		result = unicode.__add__( self, other )
		if ISanitizedHTMLContentFragment.providedBy( other ):
			result = SanitizedHTMLContentFragment( result )
		elif IHTMLContentFragment.providedBy( other ):
			result = HTMLContentFragment( result )
		# TODO: What about the rules for the other types?
		return result

class IPlainTextContentFragment(IUnicodeContentFragment,mime_types.IContentTypeTextPlain):
	"""
	Interface representing content in plain text format.
	"""

@interface.implementer(IPlainTextContentFragment)
class PlainTextContentFragment(UnicodeContentFragment):
	pass
